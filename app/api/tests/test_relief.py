"""A vineyard's relief (relief.py, routers/relief.py): elevation, slope and aspect from terrain tiles, here made-up
ones (a hillside tilted a known way), so nothing is fetched."""
import io
import math

import numpy as np
import pytest

import relief
from db import Producer, Region, Vineyard, Wine
from tests.test_maintenance import wait


def seed(s):
    rhone = Region(name="Rhone", country="France")
    v = Vineyard(name="La Landonne", region_obj=rhone)
    s.add_all([v, Wine(producer=Producer(name="Guigal"), cuvee="La Landonne", vintage="2016", region_obj=rhone,
                       vineyard=v)])


def square(x, y, d):
    return {"type": "Polygon", "coordinates": [[[x, y], [x + d, y], [x + d, y + d], [x, y + d], [x, y]]]}


def plane(slope_deg, facing_deg, lat=45.49):
    """get(z, x, y) for a hillside of `slope_deg` going down towards `facing_deg` (0 north, 90 east)"""
    t = math.tan(math.radians(slope_deg))
    down_e, down_n = math.sin(math.radians(facing_deg)), math.cos(math.radians(facing_deg))

    def get(z, x, y):
        m = relief.pixel_m(z, lat)
        ox, oy = relief._world(4.78, 45.5, z)  # near the outline: small numbers, as real elevations are
        cols = (x * relief.SIZE + np.arange(relief.SIZE) - ox) * m  # metres east
        rows = (y * relief.SIZE + np.arange(relief.SIZE) - oy) * m  # metres south
        east, south = np.meshgrid(cols, rows)
        return (500 - t * (east * down_e - south * down_n)).astype(np.float32)
    return get


OUTLINE = square(4.783, 45.488, 0.003)  # ~230 m by 330 m above Ampuis


@pytest.mark.parametrize("slope,facing,point", [(10, 90, "E"), (25, 135, "SE"), (5, 200, "SSW")])
def test_a_tilted_hillside(slope, facing, point):
    import shapely
    found = relief.compute(shapely.from_geojson(__import__("json").dumps(OUTLINE)), get=plane(slope, facing))
    assert found["slope"]["median"] == pytest.approx(slope, abs=0.3)
    assert found["aspect"] == pytest.approx(facing, abs=1)
    assert relief.compass(found["aspect"]) == point
    assert found["zoom"] == relief.MAX_ZOOM
    assert found["elevation"]["min"] < found["elevation"]["mean"] < found["elevation"]["max"]


def test_flat_land_faces_nowhere():
    import shapely
    flat = lambda z, x, y: np.full((relief.SIZE, relief.SIZE), 120, np.float32)  # noqa: E731
    found = relief.compute(shapely.from_geojson(__import__("json").dumps(OUTLINE)), get=flat)
    assert found["aspect"] is None and found["slope"]["median"] == 0
    assert found["elevation"] == {"min": 120, "mean": 120, "max": 120}


def test_terrarium_decoding():
    from PIL import Image
    v = 284.5 + 32768  # R*256 + G + B/256
    px = np.array([[[int(v // 256), int(v % 256), int((v % 1) * 256)]]], np.uint8)
    buf = io.BytesIO()
    Image.fromarray(px).save(buf, "PNG")
    assert relief.decode(buf.getvalue())[0, 0] == pytest.approx(284.5)


def test_a_vineyard_page_works_it_out_once(client, monkeypatch):
    calls = []

    def fake(z, x, y):
        calls.append((z, x, y))
        return plane(12, 112)(z, x, y)
    monkeypatch.setattr(relief, "fetch", fake)
    assert client.get("/api/vineyards/1/relief").json() is None  # no outline yet
    client.put("/api/vineyards/1/outline", json={"geometry": OUTLINE})
    r = client.get("/api/vineyards/1/relief").json()
    assert r["facing"] == "ESE" and r["slope"]["median"] == pytest.approx(12, abs=0.3)
    n = len(calls)
    assert client.get("/api/vineyards/1/relief").json() == r  # kept: nothing fetched again
    assert len(calls) == n
    # the outline drawn again: worked out again
    client.put("/api/vineyards/1/outline", json={"geometry": square(4.784, 45.488, 0.002)})
    client.get("/api/vineyards/1/relief")
    assert len(calls) > n


def test_unreachable_tiles(client, monkeypatch):
    def down(z, x, y):
        raise OSError("no network")
    monkeypatch.setattr(relief, "fetch", down)
    client.put("/api/vineyards/1/outline", json={"geometry": OUTLINE})
    assert client.get("/api/vineyards/1/relief").status_code == 503
    assert client.get("/api/vineyards/999/relief").status_code == 404


def test_the_maintenance_task(client, monkeypatch):
    monkeypatch.setattr(relief, "fetch", plane(8, 270))
    client.put("/api/vineyards/1/outline", json={"geometry": OUTLINE})
    client.post("/api/maintenance/reliefs", json={"commit": True})
    job = wait(client)
    assert "1 vineyard" in job["result"]["summary"], job
    assert job["result"]["items"][0]["detail"].startswith("W ·")
    assert client.get("/api/vineyards/1/relief").json()["facing"] == "W"


def test_a_lower_zoom_where_the_fine_tiles_stop():
    """Outside the fine models (Piedmont), z15 is a 404: worked out at z14"""
    import json
    from urllib.error import HTTPError
    import shapely
    hill = plane(15, 180)

    def get(z, x, y):
        if z > 14:
            raise HTTPError("u", 404, "Not Found", None, None)
        return hill(z, x, y)
    found = relief.compute(shapely.from_geojson(json.dumps(OUTLINE)), get=get)
    assert found["zoom"] == 14 and relief.compass(found["aspect"]) == "S"
    assert found["slope"]["median"] == pytest.approx(15, abs=0.5)


def test_contours_inside_the_outline(client, monkeypatch):
    """A hillside tilted 10° towards the east: north-south contour lines inside the outline, a handful of them,
    served for the maps"""
    import json
    import shapely
    found = relief.compute(shapely.from_geojson(json.dumps(OUTLINE)), get=plane(10, 90))
    lines = found["contours"]["lines"]
    bands = found["contours"]["bands"]
    whole = shapely.from_geojson(json.dumps(OUTLINE))
    assert len(bands) >= 8 and sum(shapely.from_geojson(json.dumps(b["area"])).area for b in bands) == pytest.approx(
        whole.area, rel=0.01)  # the outline cut into bands, all of it
    assert min(b["t"] for b in bands) < 0.15 and max(b["t"] for b in bands) > 0.85
    assert 2 <= len(lines) <= relief.MAX_LINES + 1
    steps = {b["ele"] - a["ele"] for a, b in zip(lines, lines[1:])}
    assert steps == {relief.interval_for(found["elevation"]["min"], found["elevation"]["max"])} or len(steps) == 1
    outline = shapely.from_geojson(json.dumps(OUTLINE)).buffer(1e-6)
    for c in lines:
        g = shapely.from_geojson(json.dumps(c["line"]))
        assert outline.contains(g)  # only inside the vineyard
        w, s, e, n = g.bounds
        assert e - w < 1e-5  # running north-south
    monkeypatch.setattr(relief, "fetch", plane(10, 90))
    client.put("/api/vineyards/1/outline", json={"geometry": OUTLINE})
    client.get("/api/vineyards/1/relief")
    fc = client.get("/api/map/vineyard-contours?ids=1,999").json()
    kinds = [f["properties"]["kind"] for f in fc["features"]]
    assert fc["type"] == "FeatureCollection" and kinds.count("line") == len(lines) and kinds.count("band") == len(bands)
    assert {f["properties"]["vineyard"] for f in fc["features"]} == {1}


def test_interval_for():
    assert relief.interval_for(100, 104) == 1
    assert relief.interval_for(176, 279) == 20
    assert relief.interval_for(43, 70) == 5


def test_an_outline_crossing_itself():
    """A bow tie (an invalid outline, as some published ones are): repaired, its relief and contours worked out"""
    import shapely
    bow = shapely.Polygon([(4.783, 45.488), (4.786, 45.491), (4.786, 45.488), (4.783, 45.491), (4.783, 45.488)])
    assert not bow.is_valid
    found = relief.compute(bow, get=plane(15, 90))
    assert found["slope"]["median"] == pytest.approx(15, abs=1) and found["contours"]["bands"]
