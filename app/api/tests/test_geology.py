"""A vineyard's geology (geology.py, routers/geology.py): BRGM's formations from the map pack's geology.parquet, as
shares of the outline; Macrostrat outside it, asked once and kept."""
import json
import os

import pytest

import geology
from db import Region, Vineyard


def seed(s):
    burgundy = Region(name="Bourgogne", country="France")
    s.add_all([Vineyard(name="Les Bressandes", region_obj=burgundy), Vineyard(name="Brunate", region_obj=burgundy)])


def write_geo(geo_dir):
    """Two formations side by side: x < 4.8607 Dalle nacrée, beyond it Oxfordian marls"""
    import pyarrow as pa
    import pyarrow.parquet as pq
    import shapely
    shapes = os.path.join(geo_dir, "shapes")
    os.makedirs(shapes)
    pieces = [("j4a", "Dalle nacrée (Callovien)", "#d9b3ff", shapely.box(4.85, 47.06, 4.8607, 47.08)),
              ("j5b", "Marnes de Bouix (Oxfordien moyen)", "#ffbfbf", shapely.box(4.8607, 47.06, 4.87, 47.08))]
    table = pa.table({"source_id": ["21:1", "21:2"], "notation": [p[0] for p in pieces],
                      "descr": [p[1] for p in pieces], "colour": [p[2] for p in pieces],
                      "display": [shapely.to_wkb(p[3]) for p in pieces]})
    pq.write_table(table, os.path.join(shapes, "geology.parquet"))
    with open(os.path.join(shapes, "manifest.json"), "w") as f:
        json.dump({"geology": {"file": "geology.parquet", "rows": 2}}, f)


def square(x, y, d):
    return {"type": "Polygon", "coordinates": [[[x, y], [x + d, y], [x + d, y + d], [x, y + d], [x, y]]]}


def test_brgm_formations_as_shares_of_the_outline(client):
    client.put("/api/vineyards/1/outline", json={"geometry": square(4.86, 47.07, 0.001)})  # 70% left of 4.8607
    g = client.get("/api/vineyards/1/geology").json()
    assert g["source"] == "brgm" and g["scale"] == "1:50,000"
    assert [(u["notation"], u["name"]) for u in g["units"]] == [("j4a", "Dalle nacrée (Callovien)"),
                                                               ("j5b", "Marnes de Bouix (Oxfordien moyen)")]
    assert [u["share"] for u in g["units"]] == pytest.approx([0.7, 0.3], abs=0.01)
    assert g["units"][0]["colour"] == "#d9b3ff"


def test_macrostrat_outside_the_pack_asked_once(client, monkeypatch):
    calls = []

    def answer(lat, lng):
        calls.append((lat, lng))
        return {"units": [{"notation": None, "name": "Impure limestone", "lithology": "limestone", "age": "Chattian",
                           "colour": "#FEE6AA", "share": 1}], "scale": "about 1:1,000,000"}
    monkeypatch.setattr(geology, "macrostrat", answer)
    assert client.get("/api/vineyards/2/geology").json() is None  # no outline
    client.put("/api/vineyards/2/outline", json={"geometry": square(7.933, 44.615, 0.002)})
    g = client.get("/api/vineyards/2/geology").json()
    assert g["source"] == "macrostrat" and g["units"][0]["age"] == "Chattian"
    assert client.get("/api/vineyards/2/geology").json() == g
    assert len(calls) == 1  # kept


def test_macrostrat_unreachable(client, monkeypatch):
    def down(lat, lng):
        raise OSError("no network")
    monkeypatch.setattr(geology, "macrostrat", down)
    client.put("/api/vineyards/2/outline", json={"geometry": square(7.933, 44.615, 0.002)})
    assert client.get("/api/vineyards/2/geology").status_code == 503
    assert client.get("/api/vineyards/999/geology").status_code == 404


def test_invalid_shapes_are_repaired(client):
    """An outline crossing itself (a bow tie) and an invalid piece of the map: shares still worked out"""
    import shapely
    bow = shapely.Polygon([(4.86, 47.07), (4.861, 47.071), (4.861, 47.07), (4.86, 47.071), (4.86, 47.07)])
    assert not bow.is_valid
    units = geology.brgm(bow)
    assert units and abs(sum(u["share"] for u in units) - 1) < 0.02
