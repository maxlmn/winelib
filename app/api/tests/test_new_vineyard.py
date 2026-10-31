"""A vineyard drawn from a wine's page (routers/outlines.py): created with its outline, linked to the wine and to
its other vintages without a vineyard."""
from db import Appellation, Producer, Region, Vineyard, Wine


def seed(s):
    burgundy = Region(name="Bourgogne", country="France")
    chambolle = Appellation(name="Chambolle-Musigny", region_obj=burgundy, subregion="Côte de Nuits")
    p = Producer(name="Domaine Roumier")
    other = Vineyard(name="Les Cras", region_obj=burgundy)
    s.add_all([Wine(producer=p, cuvee="Les Amoureuses", vintage="2019", type="Red", appellation=chambolle,
                    region_obj=burgundy),
               Wine(producer=p, cuvee="Les Amoureuses", vintage="2018", type="Red", appellation=chambolle),
               Wine(producer=p, cuvee="Les Amoureuses", vintage="2017", type="Red", appellation=chambolle,
                    vineyard=other),  # has one: kept
               Wine(producer=p, cuvee="Bonnes-Mares", vintage="2019", type="Red", appellation=chambolle)])


SQUARE = {"type": "Polygon", "coordinates": [[[4.95, 47.17], [4.96, 47.17], [4.96, 47.18], [4.95, 47.18], [4.95, 47.17]]]}


def test_start(client):
    st = client.get("/api/wines/1/new-vineyard").json()
    assert (st["name"], st["region"], st["appellation"]) == ("Les Amoureuses", "Bourgogne", "Chambolle-Musigny")
    assert st["frame"] and st["custom"] is None and st["wine"]["vintage"] == "2019"
    assert client.get("/api/wines/99/new-vineyard").status_code == 404


def test_refused(client):
    assert client.post("/api/vineyards", json={"wine": 1, "name": " ", "geometry": SQUARE}).status_code == 422
    assert client.post("/api/vineyards", json={"wine": 1, "name": "X", "geometry": {"type": "Point",
                                                                                    "coordinates": [4, 47]}}).status_code == 422


def test_create_links_the_wine_and_its_vintages(client):
    r = client.post("/api/vineyards", json={"wine": 1, "name": "Les Amoureuses", "village": "Chambolle-Musigny",
                                            "geometry": SQUARE})
    assert r.status_code == 201 and r.json()["wines_linked"] == 2
    vid = r.json()["id"]
    v = client.get(f"/api/vineyards/{vid}").json()
    assert (v["name"], v["village"], v["region"], v["subregion"]) == ("Les Amoureuses", "Chambolle-Musigny",
                                                                      "Bourgogne", "Côte de Nuits")
    assert client.get("/api/wines/1").json()["vineyard"]["id"] == vid
    assert client.get("/api/wines/2").json()["vineyard"]["id"] == vid
    assert client.get("/api/wines/3").json()["vineyard"]["name"] == "Les Cras"  # kept its own
    assert client.get("/api/wines/4").json()["vineyard"] is None  # another cuvée
    outline = client.get(f"/api/vineyards/{vid}/outline").json()
    assert outline["boundary"].startswith("custom:") and outline["custom"]["type"] in ("Polygon", "MultiPolygon")
    shapes = client.get(f"/api/vineyards/{vid}/shapes").json()
    assert shapes["vineyards"]["features"]  # drawn on its page's map


def test_change_a_wines_vineyard(client):
    """A wine with a vineyard (Change its vineyard): the one drawn replaces it, on its vintages with the same one too;
    a vintage with another vineyard keeps its own"""
    first = client.post("/api/vineyards", json={"wine": 1, "name": "Old", "geometry": SQUARE}).json()["id"]
    assert client.get("/api/wines/1/new-vineyard").json()["wine"]["vineyard"] == "Old"
    r = client.post("/api/vineyards", json={"wine": 1, "name": "Les Amoureuses", "geometry": SQUARE})
    assert r.status_code == 201 and r.json()["wines_linked"] == 2
    new = r.json()["id"]
    assert new != first
    assert client.get("/api/wines/1").json()["vineyard"]["id"] == new
    assert client.get("/api/wines/2").json()["vineyard"]["id"] == new  # had the old one: moved too
    assert client.get("/api/wines/3").json()["vineyard"]["name"] == "Les Cras"  # its own: kept
