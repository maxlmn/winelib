"""A wine without a cuvée name is stored as '' (older wines) or NULL (added from the form before the fix):
they're one cuvée for the wine page's vintages, the tasting page's history and duplicate detection."""
import datetime

from db import Appellation, Bottle, Producer, TastingNote, Wine


def seed(s):
    p = Producer(name="Domaine Jamet")
    cr = Appellation(name="Côte-Rôtie")
    s.add_all([Wine(producer=p, cuvee="", appellation=cr, vintage="2021", type="Red"),
               Wine(producer=p, cuvee=None, appellation=cr, vintage="2022", type="Red"),
               Wine(producer=p, cuvee="Côte Brune", appellation=cr, vintage="2022", type="Red")])
    s.flush()
    b21, b22 = Bottle(wine_id=1, qty=0, location="Consumed"), Bottle(wine_id=2, qty=0, location="Consumed")
    s.add_all([b21, b22])
    s.flush()
    s.add_all([TastingNote(bottle=b21, date=datetime.date(2025, 1, 1), notes="2021"),
               TastingNote(bottle=b22, date=datetime.date(2026, 1, 1), notes="2022")])


def test_wine_page_lists_both_vintages(client):
    assert sorted(v["vintage"] for v in client.get("/api/wines/2").json()["vintages"]) == ["2021", "2022"]
    assert sorted(v["vintage"] for v in client.get("/api/wines/1").json()["vintages"]) == ["2021", "2022"]


def test_tasting_history_spans_both(client):
    assert [h["notes"] for h in client.get("/api/tastings/2").json()["history"]] == ["2021"]


def test_form_saves_a_blank_cuvee_as_empty(client):
    w = client.post("/api/wines", json={"producer": 1, "cuvee": "  ", "vintage": "2023", "type": "Red", "appellation": 1})
    assert w.status_code == 201, w.text
    assert client.get(f"/api/wines/{w.json()['id']}").json()["cuvee"] == ""
    assert "2023" in [v["vintage"] for v in client.get("/api/wines/1").json()["vintages"]]
