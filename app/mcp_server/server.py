"""WineLib for AI assistants: an MCP server that reads your cellar, tastings, wishlist and maps through WineLib's API.

Read-only: it asks the running app (its /api), never the database, so it works with any installation it can reach
(your computer, a NAS over Tailscale). Claude Desktop, Claude Code or any MCP client starts it:

    python app/mcp_server/server.py                      # WINELIB_URL, else http://localhost:8000
    WINELIB_URL=https://nas.example.ts.net python app/mcp_server/server.py

Its requirements: app/mcp_server/requirements.txt. Setup for each client: app/mcp_server/README.md.
"""
import logging
import os
import re
import unicodedata
from datetime import date

import httpx
import hashlib
import json

from mcp.server.mcpserver import Context, MCPServer
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

URL = os.environ.get("WINELIB_URL", "http://localhost:8000").rstrip("/")
logging.getLogger("httpx").setLevel(logging.WARNING)  # not a line per request
READ = ToolAnnotations(readOnlyHint=True, openWorldHint=False)
# Tools that add to WineLib (never remove or change what's there): each asks the user first, then adds
WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False)

mcp = MCPServer(
    name="WineLib",
    instructions=(
        "WineLib is the user's wine cellar and tasting journal. Use these tools to answer questions about the bottles "
        "they own (and where they are), the wines they've tasted (when, where, their score and notes), their lists "
        "(wishlist, critics' lists, classifications) and progress on them, "
        "and wine regions. Wines, producers and places have ids: pass them to wine() for the details. Scores like "
        "'RP 95' are critics' (RP: Robert Parker); a tasting's rating is the user's own, out of 100. Everything here is "
        "read-only, except create_list and add_to_list: they show the user what they'll do and wait for the user's "
        "yes, then add (never remove or change anything; what they add can be removed in the app). Find the wines "
        "first (tastings, cellar, search), then pass their ids."
    ),
)


def get(path, **params):
    """GET a WineLib API path (JSON). A clear error when the app can't be reached."""
    try:
        r = httpx.get(f"{URL}{path}", params={k: v for k, v in params.items() if v not in (None, "")}, timeout=30)
    except httpx.HTTPError as e:
        raise RuntimeError(f"WineLib isn't reachable at {URL} ({e}). Is it running? Set WINELIB_URL.") from e
    if r.status_code == 404:
        raise ValueError("Not found in WineLib")
    r.raise_for_status()
    return r.json()


def fold(s):
    """For matching: lower case, no accents."""
    return unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()


def matches(row, query, *keys):
    """Every word of the query in one of the row's fields."""
    hay = " ".join(fold(row.get(k)) for k in keys)
    return all(w in hay for w in fold(query).split())


def wine_name(r):
    return " ".join(x for x in (r.get("producer"), r.get("cuvee"), r.get("vintage")) if x)


@mcp.tool(annotations=READ)
def search(query: str) -> list[dict]:
    """Find anything in WineLib by name: wines ("rougeard bourg 2016"), producers, appellations, regions, grapes,
    vineyards and places (restaurants, homes). Each result has a kind and an id."""
    return [{k: r.get(k) for k in ("kind", "id", "title", "sub")} for r in get("/api/search", q=query, limit=8)["results"]]


@mcp.tool(annotations=READ)
def cellar(query: str = "", color: str = "", region: str = "", storage: str = "", ready_only: bool = False,
           limit: int = 60) -> dict:
    """The bottles the user owns now, one line per wine and location: producer, cuvée, vintage, appellation, region,
    colour (Red, White, Bubbles, Rose, Sweet...), bottles, where they are (bin and storage place), critics' scores and
    whether it's ready to drink. Filter by words (producer, cuvée, appellation, grape), colour, region, storage place
    (e.g. "Home"), or only the ready ones. Totals cover every match; lines stop at `limit`."""
    rows = get("/api/cellar")["bottles"]
    rows = [r for r in rows if r["qty"] > 0
            and (not query or matches(r, query, "producer", "cuvee", "appellation", "varietal", "vintage", "region"))
            and (not color or fold(color) in fold(r.get("color")))
            and (not region or fold(region) in fold(r.get("region")))
            and (not storage or fold(storage) in fold(r.get("location_group")) or fold(storage) == fold(r.get("location")))
            and (not ready_only or r.get("maturity") == "ready")]
    lines = [{"wine_id": r["wine_id"], "wine": wine_name(r), "appellation": r.get("appellation"), "region": r["region"],
              "color": r.get("color"), "format": r.get("format"), "bottles": r["qty"], "bin": r["location"],
              "storage": r["location_group"], "scores": r.get("scores"), "maturity": r.get("maturity"),
              "drink": [r.get("drink_from") or None, r.get("drink_to") or None]} for r in rows]
    return {"bottles": sum(r["qty"] for r in rows), "lines": len(lines), "shown": lines[:limit]}


@mcp.tool(annotations=READ)
def what_to_open(storage: str = "", color: str = "") -> dict:
    """Ideas for what to open: the bottles to drink soon (past or near the end of their drinking window), and the
    ready ones, optionally only those in one storage place ("Home") or of one colour."""
    soon = get("/api/dashboard")["drink_soon"]["lines"]
    # The drink-soon lines name the bin (H7); the cellar's lines say which storage place it's in (Home)
    group = {b["bottle_id"]: b["location_group"] for b in get("/api/cellar")["bottles"]}
    soon = [r for r in soon if (not storage or fold(storage) in fold(group.get(r.get("bottle_id"))) or fold(storage) == fold(r.get("location")))
            and (not color or fold(color) in fold(r.get("color")))]
    ready = cellar(color=color, storage=storage, ready_only=True, limit=25)
    return {"drink_soon": [{"wine_id": r["wine_id"], "wine": wine_name(r), "appellation": r.get("appellation"),
                            "bottles": r["qty"], "bin": r["location"], "maturity": r.get("maturity"),
                            "years_left": r.get("years_left"), "scores": r.get("scores")} for r in soon],
            "ready": ready["shown"]}


@mcp.tool(annotations=READ)
def wine(wine_id: int) -> dict:
    """One wine in full: producer, cuvée, vintage, colour, region, appellation, vineyard, grapes, critics' scores and
    reviews' links, drinking window, every vintage of the cuvée (owned, tasted, scores), the bottles in the cellar and
    the user's tastings of it."""
    w = get(f"/api/wines/{wine_id}")
    return {
        "id": w["id"], "producer": w["producer"], "cuvee": w["cuvee"], "vintage": w["vintage"], "color": w["color"],
        "region": w.get("region"), "appellation": (w.get("appellation") or {}).get("name"),
        "vineyard": (w.get("vineyard") or {}).get("label"), "grapes": [g["name"] for g in w.get("grapes") or []],
        "blend": w.get("blend"), "lwin": w.get("lwin"), "drink_window": w.get("drink_window"), "maturity": w.get("maturity"),
        "critics": [{k: s.get(k) for k in ("critic", "score", "url")} for s in w.get("scores") or []],
        "vintages": [{k: v.get(k) for k in ("id", "vintage", "bottles", "tastings", "scores")} for v in w.get("vintages") or []],
        "cellar": [{"wine_id": b["wine_id"], "vintage": b["vintage"], "bottles": b["qty"], "bin": b["location"],
                    "storage": b["location_group"], "format": b.get("format")} for b in w.get("cellar") or []],
        "tastings": [{"date": t.get("date"), "vintage": t.get("vintage"), "rating": t.get("rating"), "notes": t.get("notes"),
                      "place": (t.get("place") or {}).get("name")} for t in w.get("tastings") or []],
        "on_wishlist": bool(w.get("wishlist")),
    }


@mcp.tool(annotations=READ)
def tastings(query: str = "", since: str = "", until: str = "", on: str = "", place: str = "", text: str = "",
             min_rating: int = 0, limit: int = 40) -> dict:
    """The user's tasting journal, newest first: date, wine, the user's rating (out of 100) and notes, and where
    (a restaurant, home, a friend's: a friend's home is a place named after them, so "with Claude" is place="Claude").
    Filter by words in the wine (producer, cuvée, appellation, grape, region), dates (since / until, YYYY-MM-DD or
    YYYY; on: one day), a place's name, words in the notes and where (text: "wow"), or a minimum rating. Each tasting
    has its wine_id, for create_list / add_to_list."""
    data = get("/api/tastings")
    places = data.get("places") or {}
    places = {str(p["id"]): p for p in places} if isinstance(places, list) else {str(k): v for k, v in places.items()}
    start = since if not re.fullmatch(r"\d{4}", since or "") else f"{since}-01-01"
    end = until if not re.fullmatch(r"\d{4}", until or "") else f"{until}-12-31"
    rows = []
    for t in sorted(data["tastings"], key=lambda t: (t.get("date") or "", t.get("seq") or 0), reverse=True):
        p = places.get(str(t.get("place_id"))) or {}
        if (query and not matches(t, query, "producer", "cuvee", "appellation", "varietal", "region", "vintage")) \
                or (start and (t.get("date") or "") < start) or (end and (t.get("date") or "") > end) \
                or (on and (t.get("date") or "") != on) or (place and fold(place) not in fold(p.get("name"))) \
                or (text and not all(w in fold(" ".join(str(t.get(k) or "") for k in ("notes", "location")) + " " + str(p.get("name") or ""))
                                     for w in fold(text).split())) \
                or (min_rating and (t.get("rating") or 0) < min_rating):
            continue
        rows.append({"date": t.get("date"), "wine_id": t.get("wine_id"), "wine": wine_name(t),
                     "appellation": t.get("appellation"), "region": t.get("region"), "color": t.get("color"),
                     "rating": t.get("rating"), "notes": t.get("notes"), "place": p.get("name"), "city": p.get("city")})
    return {"tastings": len(rows), "shown": rows[:limit]}


def _entries(detail):
    return [{"entry": i["kind"], "producer": (i.get("producer") or {}).get("name"),
             "wine": (i.get("wine") or {}).get("cuvee") if i["kind"] != "producer" else None,
             "vintage": (i.get("wine") or {}).get("vintage") if i["kind"] == "wine" else None,
             "wine_id": (i.get("wine") or {}).get("id"), "region": i.get("region"), "note": i.get("note"),
             "tasted": i["tasted"], "last_tasted": i.get("last_tasted"), "best_rating": i.get("best_rating"),
             "owned": i["owned"]} for i in detail["items"]]


@mcp.tool(annotations=READ)
def lists(name: str = "") -> dict:
    """The user's lists of wines to find and taste (a critic's top 100, Noble Rot's wines of the decade, a
    classification, their wishlist...): each with its progress. With a name (or part of it), that list's entries:
    a wine (that vintage), a cuvée (any vintage) or a producer (any of its wines), each tasted or not (from the
    user's tastings), the bottles owned, and its note (often a rank or a tier)."""
    found = get("/api/lists")
    if not name:
        return {"lists": [{k: lst.get(k) for k in ("id", "name", "source", "entries", "tasted", "owned", "is_wishlist")}
                          for lst in found]}
    match = [lst for lst in found if fold(name) in fold(lst["name"])]
    if not match:
        return {"error": f"No list named like “{name}”", "lists": [lst["name"] for lst in found]}
    d = get(f"/api/lists/{match[0]['id']}")
    return {k: d.get(k) for k in ("name", "source", "description", "entries", "tasted", "owned")} | {"items": _entries(d)}


@mcp.tool(annotations=READ)
def wishlist() -> list[dict]:
    """The wines the user would like (their wishlist, one of their lists): each tasted or not, owned or not, with
    its note."""
    wl = next((lst for lst in get("/api/lists") if lst.get("is_wishlist")), None)
    return _entries(get(f"/api/lists/{wl['id']}")) if wl else []


@mcp.tool(annotations=READ)
def region(name: str) -> dict:
    """A wine region (e.g. "Bourgogne", "Loire"): what the user holds and has tasted from it, by appellation and
    producer."""
    r = get(f"/api/regions/{name}")
    return {"name": r["name"], "country": r.get("country"), "stats": r.get("stats"),
            "appellations": [a for a in r.get("appellations") or [] if a.get("bottles") or a.get("tastings")],
            "producers": [{k: p.get(k) for k in ("id", "name", "village", "bottles", "tastings")}
                          for p in r.get("producers") or [] if p.get("bottles") or p.get("tastings")]}


@mcp.tool(annotations=READ)
def producer(producer_id: int) -> dict:
    """A producer: where they are, the lists they're on, and their cuvées in WineLib, each with its vintages (owned,
    tasted, critics' scores)."""
    p = get(f"/api/producers/{producer_id}")
    keep = ("id", "name", "region", "subregion", "village", "winemaker", "owner", "type", "website", "description", "lists")
    out = {k: p.get(k) for k in keep if p.get(k)}
    out["cuvees"] = [{"cuvee": w.get("cuvee"), "color": w.get("color"), "appellation": (w.get("appellation") or {}).get("name"),
                      "grape": w.get("varietal"),
                      "vintages": [{k: v.get(k) for k in ("id", "vintage", "bottles", "tastings", "scores")}
                                   for v in w.get("vintages") or []]}
                     for w in p.get("wines") or []]
    return out


def post(path, body=None):
    try:
        r = httpx.post(f"{URL}{path}", json=body, timeout=60)
    except httpx.HTTPError as e:
        raise RuntimeError(f"WineLib isn't reachable at {URL} ({e})") from e
    if r.status_code >= 400:
        raise ValueError(r.json().get("detail") if "json" in r.headers.get("content-type", "") else r.text)
    return r.json()


class Entry(BaseModel):
    """One entry for a list: a wine (that vintage), a cuvée (any vintage of the wine's cuvée) or a producer."""
    kind: str = Field("wine", description='"wine" (that vintage), "cuvee" (any vintage) or "producer"')
    wine_id: int | None = Field(None, description="the wine (for wine and cuvee)")
    producer_id: int | None = Field(None, description="the producer (for producer)")
    note: str | None = Field(None, description="a note: why it's there, a rank, a date")


class Confirm(BaseModel):
    confirm: bool = Field(description="Do it")


def _describe(entries):
    lines = []
    for e in entries:
        if e.kind == "producer":
            label = f"{get(f'/api/producers/{e.producer_id}')['name']} (any of its wines)"
        else:
            w = get(f"/api/wines/{e.wine_id}")
            label = " ".join(x for x in (w["producer"]["name"], w["cuvee"], w["vintage"] if e.kind == "wine" else "") if x)
            label += " (any vintage)" if e.kind == "cuvee" else ""
        lines.append(label + (f" · “{e.note}”" if e.note else ""))
    return lines


def _token(*parts):
    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()[:12]


async def _confirmed(ctx, message, token, given):
    """The user's yes: through the client's own confirmation (MCP elicitation) when it has one; else a token the
    tool returns with the preview, accepted only when called again with it (after the user said yes)."""
    if given:
        return given == token
    try:
        result = await ctx.elicit(message, Confirm)
    except Exception:  # the client can't ask: the preview goes back, the user answers in the conversation
        return {"needs_confirmation": True, "preview": message, "confirm_token": token,
                "how": "Show the user this preview. Only if they say yes, call the tool again with the same arguments "
                       "and confirm_token."}
    return result.action == "accept" and bool(getattr(result.data, "confirm", False))


def _add(list_id, entries):
    added = 0
    for e in entries:
        body = {"kind": e.kind, "note": e.note}
        body.update({"producer_id": e.producer_id} if e.kind == "producer" else {"wine_id": e.wine_id})
        added += 0 if post(f"/api/lists/{list_id}/items", body).get("existing") else 1
    return added


def _plural(n):
    return f"{n} entr{'y' if n == 1 else 'ies'}"


@mcp.tool(annotations=WRITE)
async def create_list(name: str, entries: list[Entry], ctx: Context, description: str = "", source: str = "",
                      confirm_token: str = "") -> dict:
    """Creates a list in WineLib with these entries ("all the wines I drank on 3 October at Claude's", "every wine
    whose note says wow"): find them first with tastings / cellar / search, then pass their wine_ids. The user sees
    the list and its entries and must say yes. Only adds (deleting the list in the app undoes it)."""
    if any(lst["name"].lower() == name.strip().lower() for lst in get("/api/lists")):
        return {"error": f"There's already a list named “{name}”: use add_to_list"}
    lines = _describe(entries)
    message = f"Create the list “{name}” with {_plural(len(lines))}:\n" + "\n".join(f"  • {x}" for x in lines)
    ok = await _confirmed(ctx, message, _token("create_list", name, [e.model_dump() for e in entries]), confirm_token)
    if ok is not True:
        return ok if isinstance(ok, dict) else {"done": False, "why": "Not confirmed: nothing was changed"}
    list_id = post("/api/lists", {"name": name.strip(), "description": description or None, "source": source or None})["id"]
    return {"done": True, "list_id": list_id, "added": _add(list_id, entries), "see": f"{URL}/lists/{list_id}",
            "undo": "Delete the list in WineLib (its page › Edit › Delete the list)"}


@mcp.tool(annotations=WRITE)
async def add_to_list(list_name: str, entries: list[Entry], ctx: Context, confirm_token: str = "") -> dict:
    """Adds entries to one of the user's lists (by its name, or part of it). The user sees what will be added and
    must say yes. An entry already on the list is kept, not doubled. Only adds (each can be removed on the list)."""
    lists_ = get("/api/lists")
    found = [lst for lst in lists_ if fold(list_name) in fold(lst["name"])]
    if len(found) != 1:
        return {"error": "Name one list" if found else f"No list named like “{list_name}”",
                "lists": [lst["name"] for lst in (found or lists_)]}
    lst = found[0]
    lines = _describe(entries)
    message = f"Add {_plural(len(lines))} to “{lst['name']}”:\n" + "\n".join(f"  • {x}" for x in lines)
    ok = await _confirmed(ctx, message, _token("add_to_list", lst["id"], [e.model_dump() for e in entries]), confirm_token)
    if ok is not True:
        return ok if isinstance(ok, dict) else {"done": False, "why": "Not confirmed: nothing was changed"}
    return {"done": True, "added": _add(lst["id"], entries), "see": f"{URL}/lists/{lst['id']}",
            "undo": "Remove the entries on the list's page"}


@mcp.tool(annotations=READ)
def today() -> str:
    """Today's date, to read "this year" or "last month" in the user's questions."""
    return date.today().isoformat()


if __name__ == "__main__":
    mcp.run()
