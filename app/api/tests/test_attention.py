"""The home page's "Needs attention" (routers/attention.py): the quick checks, each with what it found and its task.
Run from app/api:  pytest"""
from db import Appellation, Bottle, Place, Producer, Region, TastingNote, Vineyard, Wine


def seed(s):
    loire = Region(name="Loire")
    saumur, sc = Appellation(name="Saumur", region_obj=loire), Appellation(name="Saumur-Champigny", region_obj=loire)
    collier = Producer(name="Domaine du Collier")
    clos = Vineyard(name="Les Clos", region_obj=loire)
    s.add_all([
        Wine(producer=collier, cuvee="La Ripaille", vintage="2017", type="Red", appellation=saumur),
        Wine(producer=collier, cuvee="La Ripaille", vintage="2017", type="Red", appellation=sc),  # under two
        Wine(producer=collier, cuvee="Charpenterie", vintage="2018", type="White", appellation=saumur, vineyard=clos),
        Wine(producer=collier, cuvee="Charpenterie", vintage="2019", type="White", appellation=saumur),  # no vineyard
        Wine(producer=collier, cuvee="Saumur Blanc", vintage="2020", type="White", appellation=saumur),
        Wine(producer=collier, cuvee="Saumur Blanc", vintage="2020", type="White", appellation=saumur),  # twice
        Place(name="Le Saint-Pierre", type="Restaurant"),  # no coordinates
        Place(name="Aaron", type="Friend's Place"),  # not meant to be on a map
    ])
    s.flush()
    s.add_all([Bottle(wine_id=1, qty=1, location="H1"), TastingNote(bottle_id=9999, notes="lost")])


def test_what_needs_attention(client):
    items = {i["id"]: i for i in client.get("/api/attention").json()["items"]}
    assert items["duplicates"]["count"] == 1 and items["duplicates"]["task"] == "duplicates"
    assert items["orphans"]["count"] == 1 and items["orphans"]["level"] == "warn"
    assert items["twice_under_two_appellations"]["count"] == 1
    assert "Domaine du Collier La Ripaille 2017" in items["twice_under_two_appellations"]["detail"]
    assert items["vineyard_gaps"]["count"] == 1 and items["vineyard_gaps"]["level"] == "info"
    assert items["places"]["count"] == 1
    assert "stale_prices" not in items and "no_lwin" not in items  # no price source here
    levels = [i["level"] for i in client.get("/api/attention").json()["items"]]
    assert levels == sorted(levels, key=lambda lv: lv != "warn")  # the warnings first
