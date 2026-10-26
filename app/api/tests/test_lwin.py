"""LWIN suggestions for the wine form, from a small Liv-ex index built like the real one."""
import json

import pytest

from db import Producer


def seed(s):
    s.add(Producer(name="Domaine Jamet"))


ENTRIES = {"jamet": [
    {"lwin": "1113824", "display_name": "Domaine Jamet, Cote Rotie", "display_name_norm": "domaine jamet cote rotie",
     "producer_name": "Domaine Jamet", "wine": "Cote Rotie", "wine_norm_light": "cote rotie", "wine_norm": "cote rotie", "colour": "Red"},
    {"lwin": "1113837", "display_name": "Domaine Jamet, Cote Rotie, Cote Brune",
     "display_name_norm": "domaine jamet cote rotie cote brune", "producer_name": "Domaine Jamet",
     "wine": "Cote Rotie, Cote Brune", "wine_norm_light": "cote rotie cote brune", "wine_norm": "cote rotie cote brune", "colour": "Red"},
]}


@pytest.fixture
def index(tmp_path, monkeypatch):
    from tasks import match_lwin
    src = tmp_path / "lookup.json"
    src.write_text(json.dumps({"domaine jamet": ENTRIES["jamet"], "jamet": ENTRIES["jamet"]}))
    db = tmp_path / "lwin.sqlite"
    match_lwin.build_index(str(src), str(db))
    monkeypatch.setattr(match_lwin, "LWIN_DB", str(db))
    monkeypatch.setattr(match_lwin.entries_for, "__defaults__", (str(db),))
    return db


def test_named_cuvee_is_exact(client, index):
    r = client.get("/api/lookups/lwin", params={"producer": "Domaine Jamet", "cuvee": "Côte Brune", "appellation": "Côte-Rôtie"}).json()
    assert r["available"] and [s["lwin"] for s in r["suggestions"]] == ["1113837"] and r["suggestions"][0]["match"] == "EXACT"


def test_no_cuvee_takes_the_plain_wine_first(client, index):
    r = client.get("/api/lookups/lwin", params={"producer": "Domaine Jamet", "appellation": "Côte-Rôtie"}).json()
    assert r["suggestions"][0]["lwin"] == "1113824"


def test_unknown_producer_and_no_index(client, index, monkeypatch):
    assert client.get("/api/lookups/lwin", params={"producer": "Nobody"}).json() == {"available": True, "suggestions": []}
    from tasks import match_lwin
    monkeypatch.setattr(match_lwin.entries_for, "__defaults__", ("/nowhere/lwin.sqlite",))
    assert client.get("/api/lookups/lwin", params={"producer": "Domaine Jamet"}).json()["available"] is False
