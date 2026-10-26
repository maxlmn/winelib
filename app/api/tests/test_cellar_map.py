"""Cellar and map endpoints. Run from app/api:  pytest"""
import datetime
import json
import os

import geo

from db import Appellation, Bottle, Producer, Region, TastingNote, Vineyard, Wine


def seed(s):
    loire = Region(name="Loire", color="#a4c96b", country="France")
    chinon = Appellation(name="Chinon", region_obj=loire, inao_id=104, boundary="inao:104")
    prod = Producer(name="Chateau de Coulaine", region_obj=loire)
    picasses = Vineyard(name="Les Picasses", vineyard_id=257, region_obj=loire, village="Chinon",
                        boundary="vineyard:loire:257")
    outside = Vineyard(name="Les Rotissants", vineyard_id=258, region_obj=loire, boundary="vineyard:loire:258")
    unmapped = Vineyard(name="Le Clos", vineyard_id=999, region_obj=loire)  # no shape: not linked
    s.add(Region(name="Nowhere"))  # nothing to map: not listed
    red = Wine(producer=prod, cuvee="Les Picasses", vintage="2020", type="Red", region_obj=loire, appellation=chinon,
               vineyard=picasses)
    nv = Wine(producer=prod, cuvee="Bulles", vintage="NV", disgorgement_date="Oct 2024", type="Bubbles", region_obj=loire)
    s.add_all([
        Bottle(wine=red, location="H10", qty=6, price=50, currency="EUR", last_price=60),
        Bottle(wine=red, location="H2", qty=2, price=40, currency="SGD"),
        Bottle(wine=nv, location="Paris", qty=1, price=30, currency="EUR"),
        Bottle(wine=nv, location="WB3", qty=0, price=30, currency="EUR"),  # drunk: excluded
    ])
    s.add_all([outside, unmapped])
    # Tasted, none left: on the tastings map only
    rot = Wine(producer=prod, cuvee="Rotissants", vintage="2019", type="Red", region_obj=loire, vineyard=outside)
    drunk = Bottle(wine=rot, location="Consumed", qty=0, price=30, currency="EUR")
    s.add_all([TastingNote(bottle=drunk, rating=90, date=datetime.date(2024, 5, 1)),
               TastingNote(bottle=drunk, rating=94, date=datetime.date(2025, 5, 1))])
    s.flush()
    s.add(TastingNote(bottle=s.query(Bottle).filter_by(location="H10").one(), rating=92, date=datetime.date(2025, 1, 1)))


def write_geo(geo_dir):
    from shapely.geometry import box
    from tests.conftest import write_store
    write_store(geo_dir, "vineyard", {"loire:257": box(0.23, 47.16, 0.24, 47.17), "loire:258": box(1.0, 47.5, 1.01, 47.51)},
                "vineyard")
    write_store(geo_dir, "inao", {"104": box(0.1, 47.1, 0.4, 47.3)})


def test_cellar_rows_and_pricing(client):
    data = client.get("/api/cellar").json()
    bottles = {b["location"]: b for b in data["bottles"]}
    assert set(bottles) == {"H10", "H2", "Paris"}

    h10 = bottles["H10"]
    assert h10["price_base"] == 50 * 1.49
    assert h10["market_base"] == 60 * 1.49  # last known market price wins
    assert bottles["H2"]["market_base"] == 40  # falls back to purchase price

    assert bottles["Paris"]["vintage"] == "NV - Oct 2024"
    assert bottles["Paris"]["local"] is False
    assert bottles["Paris"]["location_group"] == "Offsite"


def test_locations_natural_order_and_capacity(client):
    locs = client.get("/api/cellar").json()["locations"]
    assert [l["name"] for l in locs] == ["H2", "H10", "Paris"]
    assert [l["capacity"] for l in locs] == [10, 10, None]


def test_regions(client):
    assert client.get("/api/regions").json() == {"Loire": "#a4c96b"}
    assert client.get("/api/region-countries").json() == {"Loire": "France"}  # Nowhere has no country


def test_map_regions_lists_only_mappable_with_your_figures(client):
    regions = client.get("/api/map/regions").json()
    assert [(r["name"], r["appellations"], r["vineyards"]) for r in regions] == [("Loire", 1, 2)]  # Le Clos: no shape
    # 9 bottles left (6 + 2 + 1), 3 tastings: the selector's cellar / tastings filters use these
    assert (regions[0]["bottles"], regions[0]["tastings"]) == (9, 3)


def loire_id(client):
    return client.get("/api/map/regions").json()[0]["id"]


def test_overview_is_one_prebuilt_outline_per_region(client):
    data = client.get("/api/map/overview").json()
    [loire] = data["features"]  # "Nowhere" has nothing to map
    assert loire["properties"]["name"] == "Loire" and loire["properties"]["kind"] == "region"
    assert loire["geometry"]["type"] in ("Polygon", "MultiPolygon")
    # From data/region_outlines.geojson: the Loire departements, Nantes to the Nievre
    w, s, e, n = loire["properties"]["bbox"]
    assert w < -1.5 and e > 3 and 46 < s < n < 48.5
    assert data["extent"] == loire["properties"]["bbox"]
    assert (loire["properties"]["bottles"], loire["properties"]["tastings"]) == (9, 3)


def test_region_outlines_file_covers_every_region_name():
    names = set(geo._region_outlines())
    assert {"Loire", "Bourgogne", "Piemonte", "Italy", "California", "Mendoza", "England"} <= names
    geom, bbox = geo.region_outline("Bourgogne")
    assert json.loads(geom)["type"] in ("Polygon", "MultiPolygon") and len(bbox) == 4
    assert geo.region_outline("Atlantis") == (None, None)


def test_overview_draws_smaller_regions_on_top(client):
    sizes = [(f["properties"]["bbox"][2] - f["properties"]["bbox"][0]) * (f["properties"]["bbox"][3] - f["properties"]["bbox"][1])
             for f in client.get("/api/map/overview").json()["features"]]
    assert sizes == sorted(sizes, reverse=True)


def test_overview_and_index_read_no_shapes(client, monkeypatch):
    geo.reset()

    def no_shapes(*_):
        raise AssertionError("shape store read")
    monkeypatch.setattr(geo, "_source", no_shapes)
    assert client.get("/api/map/overview").status_code == 200
    assert client.get(f"/api/map/regions/{loire_id(client)}").status_code == 200


def test_unchanged_index_is_a_304(client):
    url = f"/api/map/regions/{loire_id(client)}"
    etag = client.get(url).headers["etag"]
    again = client.get(url, headers={"if-none-match": etag})
    assert again.status_code == 304 and again.content == b""
    assert client.get("/api/map/overview", headers={"if-none-match": etag}).status_code == 200


def test_cellar_is_read_once_for_both_kinds(client, monkeypatch):
    import cellar
    import routers.map as map_router
    calls = []
    real = cellar.load_cellar
    url = f"/api/map/regions/{loire_id(client)}"
    monkeypatch.setattr(map_router, "load_cellar", lambda s: calls.append(1) or real(s))
    client.get(url)
    assert len(calls) == 1


def test_map_region_is_an_index_without_geometry(client):
    data = client.get(f"/api/map/regions/{loire_id(client)}").json()
    assert [a["name"] for a in data["appellations"]] == ["Chinon"]
    assert data["extent"] == geo.region_outline("Loire")[1]  # the region outline's
    assert data["outline"]["type"] in ("Polygon", "MultiPolygon")
    assert "geometry" not in data["appellations"][0] and "bbox" not in data["appellations"][0]
    index = {v["name"]: v for v in data["vineyards"]}
    assert set(index) == {"Les Picasses", "Les Rotissants"}  # Le Clos has no shape: not listed
    assert (index["Les Picasses"]["village"], index["Les Picasses"]["bottles"]) == ("Chinon", 8)
    assert (index["Les Rotissants"]["tastings"], index["Les Rotissants"]["bottles"]) == (2, 0)
    assert "score" not in index["Les Rotissants"]  # your ratings stay off screen for now
    assert data["appellations"][0]["tastings"] == 1
    assert "geometry" not in index["Les Picasses"]


def le_clos_id(client):
    return next(i for i in range(1, 10) if client.get(f"/api/vineyards/{i}").json().get("name") == "Le Clos")


def test_shapes_for_drawn_ids_are_geometries_only(client):
    index = {v["name"]: v["id"] for v in client.get(f"/api/map/regions/{loire_id(client)}").json()["vineyards"]}
    data = client.post("/api/map/shapes", json={"appellations": [1], "vineyards": [index["Les Picasses"], le_clos_id(client)]}).json()
    assert data["appellations"]["1"]["type"] == "Polygon"
    assert data["vineyards"][str(index["Les Picasses"])]["type"] == "Polygon"
    assert data["vineyards"][str(le_clos_id(client))] is None  # no shape
    assert data["version"] == client.get(f"/api/map/regions/{loire_id(client)}").json()["version"]
    empty = client.post("/api/map/shapes", json={}).json()
    assert empty["appellations"] == empty["vineyards"] == {}


def test_store_files_are_read_once(client, monkeypatch):
    import pyarrow.parquet as pq
    geo.reset()
    reads = []
    real = pq.read_table
    monkeypatch.setattr(pq, "read_table", lambda *a, **k: reads.append(a[0]) or real(*a, **k))
    first = client.post("/api/map/shapes", json={"appellations": [1]}).json()
    assert client.post("/api/map/shapes", json={"appellations": [1]}).json() == first
    assert len(reads) == 1  # the INAO store file, once


def test_version_follows_the_store_and_the_links(client):
    import json as json_
    before = client.get(f"/api/map/regions/{loire_id(client)}").json()["version"]
    path = os.path.join(geo.SHAPES_DIR, "manifest.json")
    manifest = json_.load(open(path))
    with open(path, "w") as f:
        json_.dump({**manifest, "rebuilt": True}, f)
    geo.reset()
    after = client.get(f"/api/map/regions/{loire_id(client)}").json()["version"]
    assert after != before  # browsers drop the shapes they kept


def test_details(client):
    index = {v["name"]: v["id"] for v in client.get(f"/api/map/regions/{loire_id(client)}").json()["vineyards"]}
    assert client.get(f"/api/vineyards/{index['Les Picasses']}").json()["village"] == "Chinon"
    assert client.get("/api/appellations/1").json()["bottles"] == 8
    assert client.get("/api/appellations/1").json()["stats"]["tastings"] == 1
    assert client.get("/api/vineyards/9999").status_code == 404
