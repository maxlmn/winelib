"""Summary dashboard aggregates."""
from datetime import date

from db import Appellation, Bottle, Place, Producer, Region, RestaurantVisit, TastingNote, Varietal, Wine
from routers.summary import vintage_key


def seed(s):
    loire = Region(name="Loire", color="#a4c96b")
    burgundy = Region(name="Bourgogne", color="#d97693")
    chinon = Appellation(name="Chinon", region_obj=loire)
    meursault = Appellation(name="Meursault", region_obj=burgundy)
    alliet = Producer(name="Philippe Alliet", region_obj=loire)
    roulot = Producer(name="Domaine Roulot", region_obj=burgundy)
    franc, pinot = Varietal(name="Cabernet Franc"), Varietal(name="Pinot Noir")
    noire = Wine(producer=alliet, cuvee="Coteau de Noire", vintage="2019", type="Red", region_obj=loire, appellation=chinon,
                 varietal=franc)
    bulles = Wine(producer=alliet, cuvee="Bulles", vintage="NV", disgorgement_date="Oct 2024", type="White", region_obj=loire)
    luchets = Wine(producer=roulot, cuvee="Luchets", vintage="2020", type="Red", region_obj=burgundy, appellation=meursault,
                   varietal=pinot)

    s.add_all([
        Bottle(wine=noire, location="H1", qty=6, price=50, currency="EUR", last_price=60),
        Bottle(wine=luchets, location="H2", qty=2, price=100, currency="SGD"),
        Bottle(wine=bulles, location="H3", qty=1, price=30, currency="SGD"),
    ])
    drunk = {w.cuvee: Bottle(wine=w, location="H4", qty=0, price=10) for w in (noire, luchets, bulles)}

    odette = Place(name="Odette", michelin_stars=3)
    zen = Place(name="Zen", michelin_stars=1)
    home = Place(name="@Home")
    s.add(Place(name="Never Been", michelin_stars=2))
    d1, d2 = date(2025, 1, 10), date(2025, 3, 5)
    s.add_all([
        TastingNote(bottle=drunk["Coteau de Noire"], place=odette, date=d1, rating=90),
        TastingNote(bottle=drunk["Coteau de Noire"], place=odette, date=d1, rating=94),  # same evening: one visit
        TastingNote(bottle=drunk["Coteau de Noire"], place=zen, date=d1),
        TastingNote(bottle=drunk["Luchets"], place=home, date=d2),
        TastingNote(bottle=drunk["Bulles"], place=home, date=d2),
        RestaurantVisit(place=odette, date=d2),  # no wine, still counts
        RestaurantVisit(place=odette, date=d1),  # already counted through the tastings
    ])


def test_tasting_kpis_and_michelin(client):
    d = client.get("/api/summary/tastings").json()
    assert d["total"] == 5 and d["wines"] == 3
    assert d["rated"] == 2 and d["avg_rating"] == 92.0
    m = d["michelin"]
    assert m["unique_stars"] == 4  # Odette 3 + Zen 1; Never Been was never visited
    assert m["total_stars"] == 7  # Odette on two days + Zen once
    assert m["restaurants"] == [{"stars": 1, "count": 1}, {"stars": 2, "count": 0}, {"stars": 3, "count": 1}]


def test_tasting_distributions(client):
    d = client.get("/api/summary/tastings").json()
    assert d["colors"] == [{"name": "Red", "count": 4}, {"name": "White", "count": 1}]
    assert d["regions"] == [{"name": "Loire", "count": 4, "color": "#a4c96b"},
                            {"name": "Bourgogne", "count": 1, "color": "#d97693"}]
    assert [(p["name"], p["count"], p["color"]) for p in d["producers"]] == [
        ("Philippe Alliet", 4, "#a4c96b"), ("Domaine Roulot", 1, "#d97693")]
    assert [(a["name"], a["count"], a["region"]) for a in d["appellations"]] == [
        ("Chinon", 3, "Loire"), ("Meursault", 1, "Bourgogne")]
    assert [(v["name"], v["count"]) for v in d["vintages"]] == [("2019", 3), ("2020", 1), ("NV", 1)]
    # each vintage split by region, for the stacked columns
    assert d["vintages"][1]["regions"] == [{"name": "Bourgogne", "count": 1, "color": "#d97693"}]
    # By grape, with the usual wine color; wines without a grape are left out
    assert d["grapes"] == [{"name": "Cabernet Franc", "count": 3, "type": "Red"}, {"name": "Pinot Noir", "count": 1, "type": "Red"}]


def test_grapes_beyond_the_top_are_summed(client, monkeypatch):
    import routers.summary as summary
    monkeypatch.setattr(summary, "TOP_GRAPES", 1)
    grapes = client.get("/api/summary/cellar").json()["grapes"]
    assert grapes == [{"name": "Cabernet Franc", "count": 6, "type": "Red"},
                      {"name": None, "count": 2, "type": None, "grapes": 1}]


def test_cellar_summary_in_sgd(client):
    d = client.get("/api/summary/cellar").json()
    assert d["total"] == 9 and d["wines"] == 3  # drunk lines excluded
    assert d["value"] == round(6 * 50 * 1.49 + 200 + 30)
    assert d["market"] == round(6 * 60 * 1.49 + 200 + 30)
    assert d["colors"] == [{"name": "Red", "count": 8}, {"name": "White", "count": 1}]
    assert [(p["name"], p["count"]) for p in d["producers"]] == [("Philippe Alliet", 7), ("Domaine Roulot", 2)]
    # NV disgorgements fold into NV
    assert [(v["name"], v["count"]) for v in d["vintages"]] == [("2019", 6), ("2020", 2), ("NV", 1)]


def test_tasting_highlights(client):
    h = client.get("/api/summary/tastings").json()["highlights"]
    # Each wine once, at its best score
    assert [(w["cuvee"], w["rating"]) for w in h["best"]] == [("Coteau de Noire", 94)]
    assert h["best"][0]["region"] == "Loire" and h["best"][0]["color"] == "Red"
    # Days at each place, with or without wine: Odette on two days, @Home and Zen on one
    assert [(p["name"], p["visits"]) for p in h["places"]] == [("Odette", 2), ("@Home", 1), ("Zen", 1)]
    # The most wines at one occasion: two at Odette on 10 Jan and two at @Home on 5 Mar, a tie the later one wins
    assert (h["evening"]["place"], h["evening"]["date"], len(h["evening"]["wines"])) == ("@Home", "2025-03-05", 2)


def test_cellar_highlights(client):
    h = client.get("/api/summary/cellar").json()["highlights"]
    assert [(w["cuvee"], w["qty"]) for w in h["largest"]] == [("Coteau de Noire", 6), ("Luchets", 2), ("Bulles", 1)]
    assert [w["vintage"] for w in h["oldest"]] == ["2019", "2020"]  # NV has no year
    assert h["storage"][0]["count"] == 9  # every bottle in one storage group here


def test_vintage_order():
    assert sorted(["NV", "2001", "1999", "n/a"], key=vintage_key) == ["n/a", "1999", "2001", "NV"]
