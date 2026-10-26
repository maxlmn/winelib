"""Outlines drawn in the app (routers/outlines.py): saved in custom_shapes, linked as custom:<id>, drawn like the
store's; deleting one puts the official link back."""
from db import Appellation, Region, Vineyard


def seed(s):
    burgundy = Region(name="Bourgogne", country="France")
    s.add_all([Appellation(name="Chambolle-Musigny", region_obj=burgundy),
               Vineyard(name="Les Amoureuses", region_obj=burgundy, vineyard_id=1, boundary="inao-pc:1")])


def square(x, y, d):
    return {"type": "Polygon", "coordinates": [[[x, y], [x + d, y], [x + d, y + d], [x, y + d], [x, y]]]}


def map_geometry(client, app_id):
    return client.post("/api/map/shapes", json={"appellations": [app_id]}).json()["appellations"][str(app_id)]


def test_draw_edit_and_delete(client):
    first = client.get("/api/appellations/1/outline").json()
    assert (first["boundary"], first["custom"], first["official"]) == (None, None, None)
    assert first["frame"] and first["frame"][0] < 4.95 < first["frame"][2]  # Bourgogne's outline: where to start
    before = client.get("/api/map/regions/1").json()["version"]

    r = client.put("/api/appellations/1/outline", json={"geometry": square(4.95, 47.17, 0.03)})
    assert r.status_code == 200 and r.json()["boundary"] == "custom:1"
    assert r.json()["bbox"] == [4.95, 47.17, 4.98, 47.2]
    assert [a["name"] for a in client.get("/api/map/regions/1").json()["appellations"]] == ["Chambolle-Musigny"]
    assert map_geometry(client, 1)["coordinates"][0][0] == [4.95, 47.17]
    edited_version = client.get("/api/map/regions/1").json()["version"]
    assert edited_version != before

    # Edited: the same outline (same link), new coordinates, and the browsers' cache version moves
    r = client.put("/api/appellations/1/outline", json={"geometry": {"type": "Feature", "geometry": square(4.9, 47.1, 0.05)}})
    assert r.json()["boundary"] == "custom:1"
    assert map_geometry(client, 1)["coordinates"][0][0] == [4.9, 47.1]
    assert client.get("/api/map/regions/1").json()["version"] != edited_version
    drawn = client.get("/api/appellations/1/outline").json()
    assert drawn["custom"]["coordinates"][0][0] == [4.9, 47.1] and drawn["frame"] == [4.9, 47.1, 4.95, 47.15]

    assert client.delete("/api/appellations/1/outline").json() == {"boundary": None}
    assert map_geometry(client, 1) is None
    assert client.delete("/api/appellations/1/outline").status_code == 404


def test_an_official_link_comes_back_after_deleting(client):
    r = client.put("/api/vineyards/1/outline", json={"geometry": square(4.96, 47.18, 0.002)})
    assert r.json()["boundary"].startswith("custom:")
    assert client.delete("/api/vineyards/1/outline").json() == {"boundary": "inao-pc:1"}


def test_bad_outlines_are_refused(client):
    line = {"type": "LineString", "coordinates": [[0, 0], [1, 1]]}
    assert client.put("/api/appellations/1/outline", json={"geometry": line}).status_code == 422
    assert client.put("/api/appellations/1/outline", json={"geometry": square(500000, 6000000, 10)}).status_code == 422
    assert client.put("/api/appellations/999/outline", json={"geometry": square(0, 0, 1)}).status_code == 404
    assert client.put("/api/producers/1/outline", json={"geometry": square(0, 0, 1)}).status_code == 404
    # a figure of eight (crossing itself) is repaired, not refused
    bowtie = {"type": "Polygon", "coordinates": [[[0, 0], [1, 1], [1, 0], [0, 1], [0, 0]]]}
    assert client.put("/api/appellations/1/outline", json={"geometry": bowtie}).status_code == 200
    client.delete("/api/appellations/1/outline")


KML = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document><Placemark><name>Les Amoureuses</name><Polygon>
<outerBoundaryIs><LinearRing><coordinates>4.95,47.17,0 4.96,47.17,0 4.96,47.18,0 4.95,47.18,0 4.95,47.17,0
</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark></Document></kml>"""


def test_files_are_read_before_saving(client):
    r = client.post("/api/outlines/parse", json={"filename": "Amoureuses.kml", "text": KML}).json()
    assert r["geometry"]["type"] == "Polygon" and [4.95, 47.17] in r["geometry"]["coordinates"][0]
    fc = {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": square(1, 1, 1)},
                                                    {"type": "Feature", "geometry": square(5, 5, 1)}]}
    r = client.post("/api/outlines/parse", json={"filename": "plots.geojson", "text": __import__("json").dumps(fc)})
    assert r.json()["geometry"]["type"] == "MultiPolygon"
    assert client.post("/api/outlines/parse", json={"filename": "x.shp", "text": ""}).status_code == 422
    assert client.post("/api/outlines/parse", json={"filename": "x.kml", "text": "<nope"}).status_code == 422
