"""The grapes directory (GET /api/grapes) and a grape's family (parents, grandparents, offspring)."""
from datetime import date

from db import Bottle, Producer, Region, TastingNote, Varietal, Wine

IDS = {}


def seed(s):
    burgundy = Region(name="Bourgogne", country="France")
    sav = Varietal(name="Savagnin", color="White", origin="France")
    pinot = Varietal(name="Pinot Noir", aliases="Pinot, Spätburgunder", color="Red", origin="France", parents="Savagnin")
    gouais = Varietal(name="Gouais Blanc", color="White", origin="Croatia")
    chard = Varietal(name="Chardonnay", color="White", origin="France", parents="Pinot Noir, Gouais Blanc", vivc=2455)
    aligote = Varietal(name="Aligoté", color="White", origin="France", parents="Pinot, Gouais Blanc")  # by an alias
    p = Producer(name="Domaine Roulot", region_obj=burgundy)
    w = Wine(producer=p, cuvee="Meursault", vintage="2019", type="White", region_obj=burgundy)
    s.add_all([sav, pinot, gouais, chard, aligote, w])
    s.flush()
    w.set_grapes([(chard, None), (aligote, None)])
    b = Bottle(wine=w, qty=3, location="H1")
    s.add_all([b, TastingNote(bottle=b, date=date(2024, 5, 1))])
    s.flush()
    IDS.update(pinot=pinot.id, chard=chard.id, aligote=aligote.id, gouais=gouais.id, sav=sav.id)


def test_every_grape_with_its_figures(client):
    rows = {r["name"]: r for r in client.get("/api/grapes").json()}
    assert set(rows) == {"Savagnin", "Pinot Noir", "Gouais Blanc", "Chardonnay", "Aligoté"}
    c = rows["Chardonnay"]
    assert (c["wines"], c["bottles"], c["tastings"], c["color"], c["origin"]) == (1, 3, 1, "White", "France")
    assert c["parents"] == ["Pinot Noir", "Gouais Blanc"]
    assert rows["Aligoté"]["wines"] == 1  # a second grape counts too
    assert rows["Gouais Blanc"]["offspring"] == 2 and rows["Pinot Noir"]["offspring"] == 2  # Aligoté names it "Pinot"
    assert rows["Savagnin"]["offspring"] == 1


def test_a_grapes_family(client):
    g = client.get(f"/api/grapes/{IDS['chard']}").json()
    assert g["vivc"]["number"] == 2455 and "vivc.de" in g["vivc"]["url"]
    parents = g["family"]["parents"]
    assert [(n["name"], n["id"]) for n in parents] == [("Pinot Noir", IDS["pinot"]), ("Gouais Blanc", IDS["gouais"])]
    assert parents[0]["parents"] == [{"name": "Savagnin", "id": IDS["sav"]}]  # a grandparent
    pinot = client.get(f"/api/grapes/{IDS['pinot']}").json()
    assert [n["name"] for n in pinot["family"]["offspring"]] == ["Aligoté", "Chardonnay"]


def test_cellar_and_tastings_carry_every_grape(client):
    """The Grape filter matches a wine by any of its grapes: the rows carry them all, main first."""
    bottle = next(b for b in client.get("/api/cellar").json()["bottles"] if b["cuvee"] == "Meursault")
    assert bottle["grapes"] == ["Chardonnay", "Aligoté"] and bottle["varietal"] == "Chardonnay"
    tasting = client.get("/api/tastings").json()["tastings"][0]
    assert tasting["grapes"] == ["Chardonnay", "Aligoté"]
