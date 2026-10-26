"""Home page. Run from app/api:  pytest"""
from datetime import date, timedelta

from db import Bottle, Place, Producer, Region, TastingNote, Wine

TODAY = date.today()


def seed(s):
    loire = Region(name="Loire", color="#a4c96b")
    rhone = Region(name="Rhone", color="#c0504d")
    jura = Region(name="Jura")
    p = Producer(name="Clos Rougeard", region_obj=loire)
    odette = Place(name="Odette", michelin_stars=3)

    def wine(region, cuvee):
        return Wine(producer=p, region_obj=region, cuvee=cuvee, vintage="2018", type="Red")

    bourg, hermitage, savagnin = wine(loire, "Le Bourg"), wine(rhone, "Hermitage"), wine(jura, "Savagnin")
    s.add_all([
        Bottle(wine=bourg, location="H1", qty=2, price=100, currency="SGD", purchase_date=TODAY - timedelta(days=3)),
        Bottle(wine=hermitage, location="H2", qty=6, price=80, currency="SGD", purchase_date=TODAY - timedelta(days=400)),
        Bottle(wine=savagnin, location="H3", qty=1, price=50, currency="SGD"),
    ])
    drunk = Bottle(wine=bourg, location="Consumed", qty=0, price=90, currency="SGD", purchase_date=TODAY)
    old = Bottle(wine=hermitage, location="WB1", qty=0, price=70, currency="SGD")
    s.add_all([
        TastingNote(bottle=drunk, date=TODAY - timedelta(days=1), place=odette, sequence=1),
        TastingNote(bottle=drunk, date=TODAY - timedelta(days=1), place=odette, sequence=2),
        TastingNote(bottle=old, date=TODAY - timedelta(days=500), location="Picnic"),
    ])


def test_dashboard(client):
    d = client.get("/api/dashboard").json()
    assert d["cellar"] == {"bottles": 9, "cost": 2 * 100 + 6 * 80 + 50, "market": 2 * 100 + 6 * 80 + 50}
    assert d["year"]["tastings"] == (2 if (TODAY - timedelta(days=1)).year == TODAY.year else 0) + (
        1 if (TODAY - timedelta(days=500)).year == TODAY.year else 0)

    first, second = d["occasions"]
    assert (first["place"], first["stars"], first["count"], len(first["wines"])) == ("Odette", 3, 2, 2)
    assert first["wines"][0]["cuvee"] == "Le Bourg" and second["place"] == "Picnic"

    # Newest purchase first; the "Consumed" bottle logged for a tasting isn't a purchase; undated ones last, newest added first
    assert [b["cuvee"] for b in d["purchases"]] == ["Le Bourg", "Hermitage", "Hermitage", "Savagnin"]
    assert d["purchases"][0]["location"] == "H1"
    # Shown instead of a missing cuvée name (none set in this seed)
    assert {"appellation", "varietal", "score", "scores"} <= set(d["purchases"][0]) and d["purchases"][0]["appellation"] is None
    assert "scores" in first["wines"][0]  # the critics' scores
    # The bottle's format, to size its bottle end (75cl by default)
    assert first["wines"][0]["format"] == "75cl" and d["purchases"][0]["format"] == "75cl"

    # Rhone: 6 bottles, last tasted 500 days ago; Jura: never tasted; Loire: tasted yesterday
    assert [(n["region"], n["bottles"]) for n in d["nudges"]] == [("Rhone", 6), ("Jura", 1)]
    assert d["nudges"][1]["last_tasted"] is None
