"""Tasting notes endpoints. Run from app/api:  pytest"""
import os
from datetime import date

import pytest

from db import Appellation, Bottle, Place, Producer, Region, RestaurantVisit, TastingNote, Varietal, Vineyard, Wine
import photos
from conftest import rp, rp_of


def seed(s):
    burgundy = Region(name="Bourgogne", color="#9e0e40")
    chambolle = Appellation(name="Chambolle-Musigny", region_obj=burgundy)
    pinot = Varietal(name="Pinot Noir")
    roumier = Producer(name="Georges Roumier", region_obj=burgundy)
    selosse = Producer(name="Jacques Selosse")
    amoureuses = Vineyard(name="Les Amoureuses", region_obj=burgundy, sub_region="Côte de Nuits", village="Chambolle-Musigny")
    w15 = Wine(producer=roumier, cuvee="Les Amoureuses", vintage="2015", type="Red", region_obj=burgundy,
               appellation=chambolle, varietal=pinot, vineyard=amoureuses, scores=rp("96", note="Gorgeous."))
    w17 = Wine(producer=roumier, cuvee="Les Amoureuses", vintage="2017", type="Red", region_obj=burgundy,
               appellation=chambolle, varietal=pinot)
    other = Wine(producer=roumier, cuvee="Bonnes-Mares", vintage="2015", type="Red", region_obj=burgundy, varietal=pinot)
    champagne = Wine(producer=selosse, cuvee="Initial", vintage="NV", disgorgement_date="Jan 2020", type="Bubbles", scores=rp("-"))

    odette = Place(name="Odette", city="Singapore", country="Singapore", type="Restaurant", michelin_stars=3, lat=1.29, lng=103.85)
    home = Place(name="@Home", city="Singapore", type="Home", lat=1.31, lng=103.81)
    nowhere = Place(name="Les Climats", city="Paris", michelin_stars=1)  # no coordinates

    def bottle(wine, **kw):
        return Bottle(wine=wine, qty=0, location="Consumed", bottle_size="75cl", **kw)

    s.add_all([
        TastingNote(bottle=bottle(champagne, price=200, currency="EUR"), date=date(2024, 3, 1), sequence=1, glasses=1.5,
                    notes="  Chalky, saline.  ", place=odette, location="Odette"),
        TastingNote(bottle=bottle(w15), date=date(2024, 3, 1), sequence=2, glasses=2, rating=97,
                    notes="Silky, rose petals.", place=odette, location="Odette"),
        TastingNote(bottle=bottle(w17), date=date(2023, 6, 10), sequence=1, rating=92, place=home, location="@Home"),
        TastingNote(bottle=bottle(other), date=date(2023, 6, 10), sequence=2, place=home, location="@Home"),
        TastingNote(bottle=bottle(w15), date=date(2022, 1, 5), sequence=1, location="A friend's place"),  # no place
        RestaurantVisit(date=date(2024, 5, 2), place=nowhere, notes="Lunch, no wine."),
    ])


def by_id(rows, **match):
    return next(r for r in rows if all(r[k] == v for k, v in match.items()))


def test_journal_rows(client):
    data = client.get("/api/tastings").json()
    rows = data["tastings"]
    assert [r["date"] for r in rows] == ["2024-03-01", "2024-03-01", "2023-06-10", "2023-06-10", "2022-01-05"]
    assert [r["seq"] for r in rows[:2]] == [1, 2]  # newest first, then in tasting order

    bubbles = rows[0]
    assert bubbles["vintage"] == "NV - Jan 2020"
    assert bubbles["notes"] == "Chalky, saline."
    assert (bubbles["producer"], bubbles["region"], bubbles["appellation"]) == ("Jacques Selosse", "Unknown", None)

    amoureuses = rows[1]
    assert (amoureuses["rating"], amoureuses["score"], amoureuses["glasses"]) == (97, "96", 2)
    assert (amoureuses["appellation"], amoureuses["varietal"], amoureuses["location"]) == ("Chambolle-Musigny", "Pinot Noir", "Odette")

    # Free-text location is used when there is no place
    friend = rows[-1]
    assert (friend["place_id"], friend["location"]) == (None, "A friend's place")


def test_journal_places_and_visits(client):
    data = client.get("/api/tastings").json()
    places = {p["name"]: p for p in data["places"].values()}
    assert set(places) == {"Odette", "@Home", "Les Climats"}  # every place a tasting or a visit refers to
    assert (places["Odette"]["stars"], places["Odette"]["lat"]) == (3, 1.29)
    assert places["@Home"]["stars"] == 0
    assert places["Les Climats"]["lat"] is None

    [visit] = data["visits"]
    assert visit == {"id": visit["id"], "date": "2024-05-02", "place_id": places["Les Climats"]["id"], "notes": "Lunch, no wine."}
    assert data["photos"] == {}


def test_detail(client):
    rows = client.get("/api/tastings").json()["tastings"]
    t = by_id(rows, date="2024-03-01", seq=2)
    d = client.get(f"/api/tastings/{t['id']}").json()

    assert (d["rating"], d["glasses"], d["notes"]) == (97, 2, "Silky, rose petals.")
    assert d["place"]["name"] == "Odette" and d["place"]["stars"] == 3

    wine = d["wine"]
    assert (wine["producer"], wine["vintage"], wine["region"], wine["region_color"]) == ("Georges Roumier", "2015", "Bourgogne", "#9e0e40")
    assert wine["appellation"]["name"] == "Chambolle-Musigny"
    assert wine["vineyard"]["label"] == "Côte de Nuits - Chambolle-Musigny - Les Amoureuses"
    assert (rp_of(wine), rp_of(wine, "note")) == ("96", "Gorgeous.")

    # The rest of that dinner, in order
    assert [(o["seq"], o["producer"]) for o in d["occasion"]] == [(1, "Jacques Selosse"), (2, "Georges Roumier")]
    # Same cuvée in other vintages and occasions, but not Bonnes-Mares
    assert [(h["date"], h["vintage"], h["place"]) for h in d["history"]] == [
        ("2023-06-10", "2017", "@Home"), ("2022-01-05", "2015", "A friend's place")]


def test_detail_bottle_price_in_sgd_and_rp_placeholder(client):
    rows = client.get("/api/tastings").json()["tastings"]
    d = client.get(f"/api/tastings/{by_id(rows, seq=1, date='2024-03-01')['id']}").json()
    assert d["bottle"]["price_base"] == pytest.approx(200 * 1.49)
    assert (d["bottle"]["price"], d["bottle"]["currency"]) == (200, "EUR")
    assert rp_of(d["wine"]) is None  # "-" means no score
    assert d["history"] == []


def test_detail_without_place_groups_by_location(client):
    rows = client.get("/api/tastings").json()["tastings"]
    d = client.get(f"/api/tastings/{by_id(rows, date='2022-01-05')['id']}").json()
    assert d["place"] is None and d["location"] == "A friend's place"
    assert [o["id"] for o in d["occasion"]] == [d["id"]]
    assert d["bottle"]["price_base"] is None


def test_detail_not_found(client):
    assert client.get("/api/tastings/9999").status_code == 404


def test_photos(client, tmp_path, monkeypatch):
    (tmp_path / "odette_2024-03-01.JPG").write_bytes(b"jpeg")
    (tmp_path / "notes.txt").write_text("not a photo")
    monkeypatch.setattr(photos, "PHOTOS_DIR", str(tmp_path))

    data = client.get("/api/tastings").json()
    src = f"/api/tastings/photos/odette_2024-03-01.JPG?v={(tmp_path / 'odette_2024-03-01.JPG').stat().st_mtime_ns // 1_000_000}"
    assert data["photos"] == {"odette_2024-03-01": src}
    t = by_id(data["tastings"], date="2024-03-01", seq=1)
    assert client.get(f"/api/tastings/{t['id']}").json()["photo"] == src

    assert client.get("/api/tastings/photos/odette_2024-03-01.JPG").content == b"jpeg"
    assert client.get("/api/tastings/photos/notes.txt").status_code == 404
    assert client.get(f"/api/tastings/photos/..%2F{os.path.basename(tmp_path)}%2Fodette_2024-03-01.JPG").status_code == 404
