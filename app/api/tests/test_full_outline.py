"""A page's own outline at full detail (geo.detail, GET /api/<kind>/<id>/outline/full): the store's `geometry`
column, one row read on request; none for a map pack's file (display outlines only) or an outline drawn in the app."""
import json

import numpy as np

from db import Appellation, Region, Vineyard


def jagged(x, y, d, n=400):
    """A square with a fine zigzag edge: the display outline smooths it, the full one keeps it."""
    import shapely
    t = np.linspace(0, d, n)
    bottom = np.column_stack([x + t, y + (np.arange(n) % 2) * d / 2000])
    ring = np.vstack([bottom, [[x + d, y + d], [x, y + d]], bottom[:1]])
    return shapely.Polygon(ring)


def write_geo(geo_dir):
    import pyarrow.parquet as pq
    from tests.conftest import write_store
    # more rows than a row group, so the lookup has to find the right group
    write_store(geo_dir, "inao", {str(i): jagged(3 + i, 47, 0.2) for i in range(150)})
    write_store(geo_dir, "eu", {"PDO-IT-A1": jagged(10, 45, 0.2)})
    path = f"{geo_dir}/shapes/eu.parquet"  # as a map pack installs it: display outlines only
    pq.write_table(pq.read_table(path).drop_columns(["geometry"]), path)


def seed(s):
    burgundy = Region(name="Bourgogne", country="France")
    s.add_all([Appellation(name="Chablis", region_obj=burgundy, boundary="inao:140"),
               Appellation(name="Barolo", region_obj=burgundy, boundary="eu:PDO-IT-A1"),
               Appellation(name="Nowhere", region_obj=burgundy),
               Vineyard(name="Drawn", region_obj=burgundy, boundary="custom:1")])


def points(geometry):
    return sum(len(ring) for ring in geometry["coordinates"])


def test_full_outline(client):
    assert client.get("/api/appellations/1").json()["full_outline"] is True
    full = client.get("/api/appellations/1/outline/full").json()
    shown = json.loads(client.post("/api/map/shapes", json={"appellations": [1]}).text)["appellations"]["1"]
    assert points(full["geometry"]) > 400 > points(shown)  # the zigzag the map smooths away
    assert full["bbox"][0] == 143 and full["bbox"][2] == 143.2  # row 140: the right row group


def test_no_full_outline(client):
    for path in ("/api/appellations/2", "/api/appellations/3", "/api/vineyards/1"):
        assert client.get(path).json()["full_outline"] is False
        assert client.get(f"{path}/outline/full").status_code == 404


def test_outlines_installed_flag(client):
    """The map and detail pages say where to get outlines when none are installed (the flag); this store has some."""
    assert client.get("/api/map/overview").json()["outlines"] is True
    assert client.get("/api/appellations/1/shapes").json()["outlines"] is True
