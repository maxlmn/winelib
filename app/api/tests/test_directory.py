"""Producer and place directories."""
from datetime import date

from db import Bottle, Place, Producer, Region, RestaurantVisit, TastingNote, Wine
from routers.directory import parse_lists


def seed(s):
    loire = Region(name="Loire", color="#a4c96b")
    burgundy = Region(name="Bourgogne", color="#d97693")
    belargus = Producer(name="Domaine Belargus", region_obj=loire, subregion="Anjou", village="Saint-Lambert",
                        winemaker="Ivan Massonnat", lists="[The New French Wine,'RP100']", notes="Chenin")
    roulot = Producer(name="Domaine Roulot", region_obj=burgundy, subregion="Cote de Beaune", village="Meursault")
    s.add(Producer(name="Unplaced", lists="[]"))  # no region

    home = Place(name="@Home", city="Singapore", country="Singapore", type="Home", lat=1.3073768, lng=103.8109121)
    odette = Place(name="Odette", city="Singapore", country="Singapore", type="Restaurant", michelin_stars=3)
    s.add(Place(name="Never Been", city="Paris", country="France", type="Bar"))

    wine = Wine(producer=belargus, cuvee="Ronceray", vintage="2020", type="White", region_obj=loire)
    drunk = Bottle(wine=wine, qty=0, location="H1")
    s.add_all([roulot, Bottle(wine=wine, qty=3, location="H2"), Bottle(wine=wine, qty=0, location="H3")])
    d1, d2 = date(2025, 1, 10), date(2025, 3, 5)
    s.add_all([
        # two bottles the same evening at home: one visit
        TastingNote(bottle=drunk, place=home, date=d1, rating=93),
        TastingNote(bottle=drunk, place=home, date=d1),
        TastingNote(bottle=drunk, place=odette, date=d1),
        TastingNote(bottle=drunk, place=odette, date=None),  # undated: not a visit
        # dinner without wine notes the same day as a tasting there: still one visit
        RestaurantVisit(place=odette, date=d1),
        RestaurantVisit(place=odette, date=d2),
    ])


def test_parse_lists():
    assert parse_lists("[The New French Wine,'RP100']") == ["The New French Wine", "RP100"]
    assert parse_lists('[,RP100]') == ["RP100"]
    assert parse_lists("[]") == [] and parse_lists(None) == []


def test_producers(client):
    rows = client.get("/api/producers").json()
    assert {r["name"] for r in rows} == {"Domaine Belargus", "Domaine Roulot", "Unplaced"}
    by_name = {r["name"]: r for r in rows}
    b = by_name["Domaine Belargus"]
    assert b["region"] == "Loire" and b["color"] == "#a4c96b"
    assert (b["subregion"], b["village"], b["winemaker"], b["notes"]) == ("Anjou", "Saint-Lambert", "Ivan Massonnat", "Chenin")
    assert b["lists"] == ["The New French Wine", "RP100"]
    assert b["tastings"] == 4
    assert b["bottles"] == 3  # only stocked lines
    assert by_name["Unplaced"]["region"] is None and by_name["Unplaced"]["lists"] == []
    assert by_name["Domaine Roulot"]["tastings"] == 0
    named = [r["name"] for r in rows if r["region"]]
    assert named == ["Domaine Roulot", "Domaine Belargus"]  # Bourgogne before Loire


def test_places_visits_count_tastings_and_restaurant_visits(client):
    rows = client.get("/api/places").json()
    assert [r["name"] for r in rows] == ["Odette", "@Home", "Never Been"]  # last visit first
    odette, home, never = rows
    assert odette["visits"] == 2 and odette["last_visit"] == "2025-03-05"
    assert odette["tastings"] == 2 and odette["stars"] == 3
    assert home["visits"] == 1 and home["last_visit"] == "2025-01-10" and home["tastings"] == 2
    assert (home["lat"], home["lng"]) == (1.30738, 103.81091)
    assert never["visits"] == 0 and never["last_visit"] is None and never["stars"] == 0
