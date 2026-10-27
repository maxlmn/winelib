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
from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

URL = os.environ.get("WINELIB_URL", "http://localhost:8000").rstrip("/")
logging.getLogger("httpx").setLevel(logging.WARNING)  # not a line per request
READ = ToolAnnotations(readOnlyHint=True, openWorldHint=False)

mcp = MCPServer(
    name="WineLib",
    instructions=(
        "WineLib is the user's wine cellar and tasting journal. Use these tools to answer questions about the bottles "
        "they own (and where they are), the wines they've tasted (when, where, their score and notes), their lists "
        "(wishlist, critics' lists, classifications) and progress on them, "
        "and wine regions. Wines, producers and places have ids: pass them to wine() for the details. Scores like "
        "'RP 95' are critics' (RP: Robert Parker); a tasting's rating is the user's own, out of 100. Everything here is "
        "read-only."
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
def tastings(query: str = "", since: str = "", place: str = "", min_rating: int = 0, limit: int = 40) -> dict:
    """The user's tasting journal, newest first: date, wine, the user's rating (out of 100) and notes, and where
    (a restaurant, home, a friend's). Filter by words (producer, cuvée, appellation, grape, region), a start date
    (YYYY-MM-DD or YYYY), a place's name, or a minimum rating."""
    data = get("/api/tastings")
    places = data.get("places") or {}
    places = {str(p["id"]): p for p in places} if isinstance(places, list) else {str(k): v for k, v in places.items()}
    start = since if not re.fullmatch(r"\d{4}", since or "") else f"{since}-01-01"
    rows = []
    for t in sorted(data["tastings"], key=lambda t: (t.get("date") or "", t.get("seq") or 0), reverse=True):
        p = places.get(str(t.get("place_id"))) or {}
        if (query and not matches(t, query, "producer", "cuvee", "appellation", "varietal", "region", "vintage")) \
                or (start and (t.get("date") or "") < start) or (place and fold(place) not in fold(p.get("name"))) \
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


@mcp.tool(annotations=READ)
def today() -> str:
    """Today's date, to read "this year" or "last month" in the user's questions."""
    return date.today().isoformat()


if __name__ == "__main__":
    mcp.run()
