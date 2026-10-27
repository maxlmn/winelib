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


def test_the_tools_are_read_only():
    import asyncio
    listed = asyncio.run(server.mcp.list_tools())
    assert {t.name for t in listed} >= {"search", "cellar", "what_to_open", "wine", "tastings", "wishlist", "region", "producer"}
    assert all(t.annotations and t.annotations.read_only_hint for t in listed)
