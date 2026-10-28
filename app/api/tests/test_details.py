"""Detail pages: producers, wines, bottles, places, appellations, vineyards and their map shapes."""
import os
from datetime import date

import pytest

from db import Appellation, Bottle, Place, Producer, Region, RestaurantVisit, TastingNote, Varietal, Vineyard, Wine
from conftest import rp, rp_of


def seed(s):
    burgundy = Region(name="Bourgogne", color="#d97693", country="France")
    loire = Region(name="Loire", color="#a4c96b", country="France")
    pinot = Varietal(name="Pinot Noir", climate="Cool", acidity="High", tannin="Low-Med", aromas="Red fruit",
               notes="Forest floor.", classic_regions="NZ : Central Otago | Germany : Baden")
    savigny = Appellation(name="Savigny-lès-Beaune", region_obj=burgundy, inao_id=173, type="AOC", boundary="inao:173",
                          pdo_id="PDO-FR-A0001", registration_date=date(1973, 9, 18), max_yield_hl=48,
                          varieties_text="Pinot Noir N, Chardonnay B", municipalities="Savigny-lès-Beaune",
                          location_link="https://example.org/savigny")
    chinon = Appellation(name="Chinon", region_obj=loire)  # no shape
    vergelesses = Vineyard(name="Les Vergelesses", vineyard_id=1193, region_obj=burgundy, boundary="vineyard:bourgogne:1193",
                           sub_region="Côte de Beaune", village="Savigny-lès-Beaune")
    chandon = Producer(name="Chandon de Briailles", region_obj=burgundy, subregion="Côte de Beaune",
                       winemaker="Claude de Nicolay", lists="['Top Burgundy', 'New French Wine']",
                       website="https://chandon.example")
    other = Producer(name="Baudry", region_obj=loire)

    def wine(vintage, **kw):
        return Wine(producer=chandon, cuvee="Les Vergelesses", vintage=vintage, type="Red", region_obj=burgundy,
                    appellation=savigny, varietal=pinot, vineyard=vergelesses, **kw)

    v2020 = wine("2020", scores=rp("93", note="Bright cherry."))
    v2019 = wine("2019", scores=rp("-"))
    v2018 = wine("2018")
    nameless = Wine(producer=chandon, cuvee=None, vintage="2021", type="White", region_obj=burgundy)
    nameless_nv = Wine(producer=chandon, cuvee=None, vintage="NV", disgorgement_date="Oct 2024", type="Bubbles",
                       region_obj=burgundy)
    baudry = Wine(producer=other, cuvee="Les Grézeaux", vintage="2019", type="Red", region_obj=loire,
                  appellation=chinon)

    home = Bottle(wine=v2020, location="H3", qty=2, price=50, currency="EUR", last_price=60, vendor="Caves",
                  provenance="Importer", purchase_date=date(2023, 5, 1), last_price_date=date(2025, 1, 2),
                  last_price_source="wine-searcher")
    drunk = Bottle(wine=v2019, location="WB2", qty=0, price=40, currency="SGD")
    wb = Bottle(wine=v2018, location="WB2", qty=1, price=100, currency="SGD")
    loire_btl = Bottle(wine=baudry, location="Paris", qty=3, price=20, currency="EUR")
    nv_btl = Bottle(wine=nameless_nv, location="H1", qty=0, price=30, currency="EUR")

    odette = Place(name="Odette", city="Singapore", country="Singapore", michelin_stars=3, lat=1.29, lng=103.85)
    s.add_all([
        TastingNote(bottle=drunk, date=date(2024, 3, 1), rating=94, notes="Lovely", place=odette, sequence=1),
        TastingNote(bottle=loire_btl, date=date(2024, 3, 1), notes="", place=odette, sequence=2),
        TastingNote(bottle=nv_btl, date=date(2023, 1, 5), location="Picnic"),
        RestaurantVisit(date=date(2024, 3, 1), place=odette, notes="Birthday"),
        RestaurantVisit(date=date(2022, 7, 7), place=odette),
        home, wb, nameless,
    ])


def write_geo(geo_dir):
    from shapely.geometry import box
    from tests.conftest import write_store
    write_store(geo_dir, "inao", {"173": box(4.8, 47.0, 4.9, 47.1)})
    write_store(geo_dir, "vineyard", {"bourgogne:1193": box(4.85, 47.05, 4.86, 47.06)}, "vineyard")


def producer_id(client, name):
    # Cellar lines carry producer ids, so tests don't depend on insertion order
    lines = client.get("/api/cellar").json()["bottles"]
    found = {b["producer"]: b["producer_id"] for b in lines}
    return found[name]


@pytest.fixture
def chandon(client):
    return client.get(f"/api/producers/{producer_id(client, 'Chandon de Briailles')}").json()


def wine_id(chandon, vintage, cuvee="Les Vergelesses"):
    fam = next(f for f in chandon["wines"] if f["cuvee"] == cuvee)
    return next(v["id"] for v in fam["vintages"] if v["vintage"] == vintage)


def test_producer_header_and_stats(chandon):
    assert chandon["region"] == "Bourgogne" and chandon["region_color"] == "#d97693"
    assert "lists" not in chandon  # the old text field: the lists themselves are on the page (/api/lists-of)
    assert chandon["stats"] == {"bottles": 3, "value": round(2 * 60 * 1.49 + 100), "tastings": 2, "wines": 5}


def test_producer_catalog_groups_vintages_by_cuvee(chandon):
    fams = {f["cuvee"]: f for f in chandon["wines"]}
    assert set(fams) == {"", "Les Vergelesses"}
    verg = fams["Les Vergelesses"]
    assert verg["appellation"]["name"] == "Savigny-lès-Beaune" and verg["varietal"] == "Pinot Noir"
    assert [(v["vintage"], v["bottles"], v["tastings"]) for v in verg["vintages"]] == [
        ("2020", 2, 0), ("2019", 0, 1), ("2018", 1, 0)]
    # NV sorts after the vintages; its label carries the disgorgement date
    assert [v["vintage"] for v in fams[""]["vintages"]] == ["2021", "NV - Oct 2024"]


def test_producer_appellations_and_vineyards(chandon):
    # Three Vergelesses vintages in Savigny: 3 bottles left (2 + 1), one tasting; the two nameless wines have neither
    assert chandon["appellations"] == [{"id": chandon["appellations"][0]["id"], "name": "Savigny-lès-Beaune",
                                        "wines": 3, "bottles": 3, "tastings": 1}]
    [verg] = chandon["vineyards"]
    assert (verg["name"], verg["village"], verg["subregion"]) == ("Les Vergelesses", "Savigny-lès-Beaune", "Côte de Beaune")
    assert (verg["wines"], verg["bottles"], verg["tastings"]) == (3, 3, 1)


def test_producer_cellar_and_history(chandon):
    assert sorted((b["location"], b["qty"]) for b in chandon["cellar"]) == [("H3", 2), ("WB2", 1)]
    history = chandon["tastings"]
    assert [t["date"] for t in history] == ["2024-03-01", "2023-01-05"]  # newest first
    first = history[0]
    assert first["rating"] == 94 and first["notes"] == "Lovely" and first["vintage"] == "2019"
    assert first["place"] == {"id": first["place"]["id"], "name": "Odette", "city": "Singapore",
                              "country": "Singapore", "type": None, "michelin_stars": 3}
    assert history[1]["place"] is None and history[1]["location"] == "Picnic"
    assert history[1]["rating"] is None


def test_wine_family_cellar_and_history(client, chandon):
    w = client.get(f"/api/wines/{wine_id(chandon, '2020')}").json()
    assert w["producer"]["name"] == "Chandon de Briailles"
    assert w["appellation"]["name"] == "Savigny-lès-Beaune"
    assert w["vineyard"]["label"] == "Côte de Beaune - Savigny-lès-Beaune - Les Vergelesses"
    assert rp_of(w) == "93" and rp_of(w, "note") == "Bright cherry."
    assert [v["vintage"] for v in w["vintages"]] == ["2020", "2019", "2018"]
    # cellar and history cover every vintage; the page filters to this one
    assert sorted(b["vintage"] for b in w["cellar"]) == ["2018", "2020"]
    assert [t["vintage"] for t in w["tastings"]] == ["2019"]


def test_wine_family_matches_null_cuvee(client, chandon):
    w = client.get(f"/api/wines/{wine_id(chandon, '2021', cuvee='')}").json()
    assert [v["vintage"] for v in w["vintages"]] == ["2021", "NV - Oct 2024"]
    assert rp_of(w) is None and w["appellation"] is None


def test_bottle_prices_and_provenance(client, chandon):
    w = client.get(f"/api/wines/{wine_id(chandon, '2020')}").json()
    b = client.get(f"/api/bottles/{w['cellar'][0]['bottle_id']}").json()
    assert b["qty"] == 2 and b["location"] == "H3" and b["location_group"] == "Home"
    assert b["price_base"] == round(50 * 1.49, 2)
    assert b["change_pct"] == 20.0
    assert (b["vendor"], b["provenance"], b["purchase_date"]) == ("Caves", "Importer", "2023-05-01")
    assert b["last_price_source"] == "wine-searcher" and b["last_price_date"] == "2025-01-02"


def test_place_stats_merge_visit_days(client, chandon):
    place_id = chandon["tastings"][0]["place"]["id"]
    p = client.get(f"/api/places/{place_id}").json()
    assert p["michelin_stars"] == 3 and (p["lat"], p["lng"]) == (1.29, 103.85)
    # 2024-03-01 has tastings and a visit: one day; 2022-07-07 is a visit alone
    assert p["stats"] == {"visits": 2, "tastings": 2, "value": round(40 + 20 * 1.49, 2)}
    assert [v["date"] for v in p["visits"]] == ["2024-03-01", "2022-07-07"]
    assert p["visits"][1]["notes"] is None
    assert [t["producer"] for t in p["tastings"]] == ["Chandon de Briailles", "Baudry"]  # by sequence
    assert p["tastings"][1]["notes"] is None  # blank notes are no notes


def test_appellation_detail_keeps_map_panel_fields(client, chandon):
    app_id = next(f for f in chandon["wines"] if f["appellation"])["appellation"]["id"]
    a = client.get(f"/api/appellations/{app_id}").json()
    panel = {"id", "name", "region", "subregion", "type", "category", "pdo_id", "registration_date",
             "max_yield_hl", "max_yield_kg", "varieties", "details", "bottles"}
    assert panel <= set(a)
    assert a["bottles"] == 3 and a["registration_date"] == "1973-09-18" and a["varieties"].startswith("Pinot")
    assert a["location_link"].startswith("https://")
    assert a["stats"]["tastings"] == 1
    assert a["producers"] == [{"id": chandon["id"], "name": "Chandon de Briailles", "wines": 3}]
    assert [(v["name"], v["wines"]) for v in a["vineyards"]] == [("Les Vergelesses", 3)]


def test_vineyard_detail(client, chandon):
    w = client.get(f"/api/wines/{wine_id(chandon, '2020')}").json()
    v = client.get(f"/api/vineyards/{w['vineyard']['id']}").json()
    assert {"id", "name", "region", "subregion", "village", "bottles"} <= set(v)
    assert (v["subregion"], v["village"], v["vineyard_id"], v["bottles"]) == ("Côte de Beaune", "Savigny-lès-Beaune", 1193, 3)
    assert [a["name"] for a in v["appellations"]] == ["Savigny-lès-Beaune"]
    assert [f["producer"] for f in v["wines"]] == ["Chandon de Briailles"]
    assert len(v["tastings"]) == 1


def test_shapes(client, chandon):
    w = client.get(f"/api/wines/{wine_id(chandon, '2020')}/shapes").json()
    assert [f["properties"]["name"] for f in w["appellations"]["features"]] == ["Savigny-lès-Beaune"]
    vine = w["vineyards"]["features"][0]["properties"]
    assert vine["name"] == "Les Vergelesses" and vine["bottles"] == 3  # gold outline: bottles held

    prod = client.get(f"/api/producers/{chandon['id']}/shapes").json()
    assert len(prod["appellations"]["features"]) == 1 and len(prod["vineyards"]["features"]) == 1

    app_id = w["appellations"]["features"][0]["id"]
    app = client.get(f"/api/appellations/{app_id}/shapes").json()
    assert [f["properties"]["name"] for f in app["vineyards"]["features"]] == ["Les Vergelesses"]


def test_region_detail_by_name_or_id(client):
    r = client.get("/api/regions/bourgogne").json()  # by name, any case
    assert (r["name"], r["country"], r["color"]) == ("Bourgogne", "France", "#d97693")
    assert client.get(f"/api/regions/{r['id']}").json()["name"] == "Bourgogne"
    assert r["stats"] == {"bottles": 3, "value": round(2 * 60 * 1.49 + 100), "tastings": 2, "producers": 1,
                          "appellations": 1, "vineyards": 1}
    assert [(a["name"], a["bottles"], a["tastings"]) for a in r["appellations"]] == [
        ("Savigny-lès-Beaune", 3, 1)]
    (chandon,) = r["producers"]
    assert (chandon["name"], chandon["wines"], chandon["bottles"], chandon["tastings"]) == ("Chandon de Briailles", 5, 3, 2)
    assert {b["location"] for b in r["cellar"]} == {"H3", "WB2"}
    assert {t["producer"] for t in r["tastings"]} == {"Chandon de Briailles"}  # the Loire bottle stays out


def test_region_shapes_have_its_outline_and_what_you_hold(client):
    s = client.get("/api/regions/Bourgogne/shapes").json()
    assert [f["properties"]["name"] for f in s["appellations"]["features"]] == ["Savigny-lès-Beaune"]
    assert [f["properties"]["name"] for f in s["vineyards"]["features"]] == ["Les Vergelesses"]
    (outline,) = s["region"]["features"]  # from app/api/data/region_outlines.geojson
    assert outline["properties"]["name"] == "Bourgogne" and outline["geometry"]["type"] in ("Polygon", "MultiPolygon")
    assert outline["properties"]["bbox"]


def test_region_shapes_top_appellations_only(client):
    s = client.get("/api/regions/Bourgogne/shapes?top=tastings").json()
    assert [f["properties"]["name"] for f in s["appellations"]["features"]] == ["Savigny-lès-Beaune"]
    assert s["vineyards"]["features"] == []  # the top list is appellations only
    assert s["region"]["features"]  # the outline stays
    assert client.get("/api/regions/Bourgogne/shapes?top=bottles&limit=0").json()["appellations"]["features"] == []


def test_grape_detail(client):
    g = client.get("/api/grapes/pinot noir").json()  # by name, any case
    assert g["name"] == "Pinot Noir"
    assert client.get(f"/api/grapes/{g['id']}").json()["name"] == "Pinot Noir"
    assert g["stats"] == {"bottles": 3, "value": round(2 * 60 * 1.49 + 100), "tastings": 1, "producers": 1,
                          "regions": 1, "wines": 3}
    assert [(r["name"], r["wines"], r["bottles"], r["tastings"]) for r in g["regions"]] == [("Bourgogne", 3, 3, 1)]
    assert [(p["name"], p["region"], p["bottles"]) for p in g["producers"]] == [("Chandon de Briailles", "Bourgogne", 3)]
    prof = g["profile"]
    assert {"label": "Climate", "value": "Cool"} in prof["facts"]
    assert prof["regions"] == ["NZ : Central Otago", "Germany : Baden"] and prof["notes"] == "Forest floor."


def test_shapes_report_missing_boundaries(client):
    baudry = client.get(f"/api/producers/{producer_id(client, 'Baudry')}/shapes").json()
    assert baudry["appellations"]["features"] == [] and baudry["appellations"]["missing"] == ["Chinon"]


@pytest.mark.parametrize("path", [
    "producers/9999", "wines/9999", "bottles/9999", "places/9999", "appellations/9999", "vineyards/9999",
    "producers/9999/shapes", "wines/9999/shapes", "appellations/9999/shapes", "vineyards/9999/shapes",
    "regions/9999", "regions/Atlantis", "regions/9999/shapes", "grapes/9999", "grapes/Nebbiolo",
])
def test_missing_ids_are_404(client, path):
    assert client.get(f"/api/{path}").status_code == 404
