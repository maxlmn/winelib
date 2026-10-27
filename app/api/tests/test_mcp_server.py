"""The MCP server (app/mcp_server/server.py): each tool, reading the API through a test client in place of HTTP.
Skipped without the MCP SDK (app/mcp_server/requirements.txt)."""
import os
import sys
from datetime import date

import pytest

pytest.importorskip("mcp")

from db import Bottle, Place, Producer, TastingNote, Wine  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "mcp_server"))
import server  # noqa: E402


def seed(s):
    p = Producer(name="Clos Rougeard")
    le_clos = Wine(producer=p, cuvee="Le Clos", vintage="2014", type="Red", drink_window_start=2020, drink_window_end=2040)
    bourg = Wine(producer=p, cuvee="Le Bourg", vintage="2016", type="Red")
    home = Place(name="Home", type="Home", city="Paris")
    s.add_all([le_clos, bourg, home])
    s.flush()
    s.add_all([Bottle(wine_id=le_clos.id, qty=2, location="H9", price=300, currency="EUR"),
               Bottle(wine_id=bourg.id, qty=1, location="WB1", price=350, currency="EUR")])
    s.flush()
    drunk = Bottle(wine_id=bourg.id, qty=0, location="Consumed")
    s.add(drunk)
    s.flush()
    s.add(TastingNote(bottle_id=drunk.id, date=date(2026, 5, 1), rating=95, notes="Iron, violets", place_id=home.id))


@pytest.fixture
def tools(client, monkeypatch):
    def get(path, **params):
        r = client.get(path, params={k: v for k, v in params.items() if v not in (None, "")})
        if r.status_code == 404:
            raise ValueError("Not found in WineLib")
        r.raise_for_status()
        return r.json()
    monkeypatch.setattr(server, "get", get)
    return server


def test_cellar_and_what_to_open(tools):
    c = tools.cellar()
    assert c["bottles"] == 3 and {line["wine"] for line in c["shown"]} == {"Clos Rougeard Le Clos 2014", "Clos Rougeard Le Bourg 2016"}
    home = tools.cellar(storage="Home")  # H bins are the tests' Home storage group
    assert [line["bin"] for line in home["shown"]] == ["H9"]
    assert tools.cellar(query="bourg 2016")["bottles"] == 1
    ready = tools.what_to_open(storage="Home")["ready"]
    assert [r["wine"] for r in ready] == ["Clos Rougeard Le Clos 2014"]


def test_wine_tastings_search(tools):
    found = tools.search("le clos 2014")
    wine_id = next(r["id"] for r in found if r["kind"] == "wine")
    w = tools.wine(wine_id)
    assert (w["cuvee"], w["vintage"], w["maturity"]) == ("Le Clos", "2014", "ready")
    t = tools.tastings(since="2026", min_rating=90)
    assert t["tastings"] == 1 and t["shown"][0]["place"] == "Home" and t["shown"][0]["notes"] == "Iron, violets"
    assert tools.tastings(place="restaurant")["tastings"] == 0
    with pytest.raises(ValueError):
        tools.wine(9999)


def test_two_tools_add_the_rest_read():
    import asyncio
    listed = asyncio.run(server.mcp.list_tools())
    assert {t.name for t in listed} >= {"search", "cellar", "what_to_open", "wine", "tastings", "lists", "wishlist", "region", "producer"}
    writes = {t.name for t in listed if not t.annotations.read_only_hint}
    assert writes == {"create_list", "add_to_list", "add_wine", "add_tasting", "add_bottle"}  # the others only read
    assert not any(t.annotations.destructive_hint for t in listed if t.name in writes)  # they only add


def test_lists_and_the_wishlist(tools, client):
    wl = client.post("/api/lists/wishlist").json()["id"]
    wine_id = next(r["id"] for r in client.get("/api/search", params={"q": "le bourg 2016"}).json()["results"] if r["kind"] == "wine")
    client.post(f"/api/lists/{wl}/items", json={"kind": "wine", "wine_id": wine_id, "note": "For 2030"})
    assert [(e["wine"], e["vintage"], e["tasted"], e["note"]) for e in tools.wishlist()] == [("Le Bourg", "2016", True, "For 2030")]
    assert tools.lists()["lists"][0]["is_wishlist"] is True
    assert tools.lists("wish")["entries"] == 1 and "error" in tools.lists("nothing like this")


class FakeCtx:
    """The client's side of a confirmation: accepts, declines, or can't ask (no elicitation)."""

    def __init__(self, answer):
        self.answer, self.asked = answer, []

    async def elicit(self, message, schema):
        self.asked.append(message)
        if self.answer == "cannot":
            raise RuntimeError("elicitation not supported")
        return type("R", (), {"action": "accept" if self.answer else "decline", "data": schema(confirm=bool(self.answer))})()


def test_writing_asks_first(tools, client, monkeypatch):
    import asyncio
    def post(path, body=None):
        r = client.post(path, json=body)
        if r.status_code >= 400:
            raise ValueError(r.json().get("detail"))
        return r.json()
    monkeypatch.setattr(tools, "post", post)
    wine_id = next(r["id"] for r in client.get("/api/search", params={"q": "le clos 2014"}).json()["results"] if r["kind"] == "wine")
    entries = [tools.Entry(kind="wine", wine_id=wine_id, note="wow")]

    # Declined: nothing written
    ctx = FakeCtx(False)
    r = asyncio.run(tools.create_list("Wow wines", entries, ctx))
    assert r["done"] is False and "Le Clos 2014" in ctx.asked[0]
    assert all(lst["name"] != "Wow wines" for lst in client.get("/api/lists").json())

    # Accepted: written, with how to undo it
    r = asyncio.run(tools.create_list("Wow wines", entries, FakeCtx(True)))
    assert r["done"] is True and r["added"] == 1 and "Delete the list" in r["undo"]

    # A client that can't ask: a preview and a token; only that token (same request) writes
    more = [tools.Entry(kind="cuvee", wine_id=wine_id)]
    r = asyncio.run(tools.add_to_list("wow", more, FakeCtx("cannot")))
    assert r["needs_confirmation"] is True and "any vintage" in r["preview"]
    assert asyncio.run(tools.add_to_list("wow", more, FakeCtx("cannot"), confirm_token="wrong"))["done"] is False
    r = asyncio.run(tools.add_to_list("wow", more, FakeCtx("cannot"), confirm_token=r["confirm_token"]))
    assert r["done"] is True and r["added"] == 1


def test_tastings_by_day_place_and_words(tools):
    assert tools.tastings(on="2026-05-01")["tastings"] == 1
    assert tools.tastings(text="violets")["tastings"] == 1 and tools.tastings(text="wow")["tastings"] == 0
    assert tools.tastings(until="2025")["tastings"] == 0


def test_a_label_to_a_tasting(tools, client, monkeypatch):
    """A label's photo read by the assistant: the names looked up (the producer reused), the wine and the tasting
    added after the user's yes; a wine already there is used, not doubled; a bottle from the cellar comes off."""
    import asyncio
    def post(path, body=None):
        r = client.post(path, json=body)
        if r.status_code >= 400:
            raise ValueError(r.json().get("detail"))
        return r.json()
    monkeypatch.setattr(tools, "post", post)
    poyeux = tools.NewWine(producer="Clos Rougeard", cuvee="Les Poyeux", vintage="2018", color="Red",
                           appellation="Saumur-Champigny", grapes=["Cabernet Franc"])

    # Declined: nothing written
    ctx = FakeCtx(False)
    r = asyncio.run(tools.add_tasting(ctx, new_wine=poyeux, notes="Graphite, cherries", place="@Mia"))
    assert r["done"] is False and "a new wine: Clos Rougeard Les Poyeux 2018" in ctx.asked[0]
    assert "producer Clos Rougeard" in ctx.asked[0] and "“Saumur-Champigny” (new)" in ctx.asked[0]
    assert "Mia’s" in ctx.asked[0]
    assert not [x for x in tools.search("poyeux 2018") if x["kind"] == "wine"]

    # Accepted: the wine (its producer the one there) and the tasting, today, at Mia's
    r = asyncio.run(tools.add_tasting(FakeCtx(True), new_wine=poyeux, notes="Graphite, cherries", place="@Mia", rating=94))
    t = client.get(f"/api/tastings/{r['tasting_id']}").json()
    assert (t["date"], t["notes"], t["rating"], t["place"]["type"]) == (date.today().isoformat(), "Graphite, cherries", 94, "Friend's Place")
    assert len([p for p in client.get("/api/lookups/producers", params={"q": "rougeard"}).json()]) == 1  # not doubled

    # The same wine again: it's there now, so it's used, not created twice
    again = asyncio.run(tools.add_wine(poyeux, FakeCtx(True)))
    assert again["already"] is True and again["wine_id"] == r["wine_id"]
    assert "Already in WineLib" in asyncio.run(tools.add_bottle(FakeCtx(True), new_wine=poyeux))["error"]

    # A bottle from the cellar opened at Home (a place it has): one fewer in the cellar
    le_clos = next(x["id"] for x in tools.search("le clos 2014") if x["kind"] == "wine")
    before = sum(x["qty"] for x in client.get(f"/api/wines/{le_clos}").json()["cellar"] if x["wine_id"] == le_clos)
    ctx = FakeCtx(True)
    asyncio.run(tools.add_tasting(ctx, wine_id=le_clos, place="Home", from_cellar=True, on="2026-10-20"))
    assert "at Home" in ctx.asked[0] and "comes off the count" in ctx.asked[0]
    after = sum(x["qty"] for x in client.get(f"/api/wines/{le_clos}").json()["cellar"] if x["wine_id"] == le_clos)
    assert after == before - 1

    # Bottles bought: in the cellar, today
    r = asyncio.run(tools.add_bottle(FakeCtx(True), wine_id=le_clos, qty=3, location="H2", price=280, currency="EUR"))
    b = client.get(f"/api/bottles/{r['bottle_id']}").json()
    assert (b["qty"], b["location"], b["price"], b["purchase_date"]) == (3, "H2", 280, date.today().isoformat())
