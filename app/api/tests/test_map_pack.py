"""The map data pack: Maintenance › Map outlines installs one into an empty store (each file checked against the
pack's checksums) and links the rows; Settings lists the credits."""
import json
import os
import time
import zipfile

from db import Appellation, Region, Vineyard


def seed(s):
    burgundy = Region(name="Bourgogne", country="France")
    s.add_all([Appellation(name="Chablis", region_obj=burgundy, inao_id=104),
               Vineyard(name="Les Amoureuses", region_obj=burgundy, vineyard_id=7)])


def wait(client):
    for _ in range(300):
        job = client.get("/api/maintenance/job").json()
        if job and job["status"] != "running":
            return job
        time.sleep(0.02)
    raise AssertionError("job didn't finish")


def build_pack(tmp_path):
    """A small pack (tests/data/map-pack.zip, made by the map pack's builder from two sources): INAO's 104 and one
    premier cru (a Weinlagen vineyard filtered out)."""
    import shutil
    out = tmp_path / "pack.zip"
    shutil.copy(os.path.join(os.path.dirname(__file__), "data", "map-pack.zip"), out)
    return out


def test_pack_then_install(client, tmp_path, monkeypatch):
    out = build_pack(tmp_path)
    assert {"pack.json", "CREDITS.md", "shapes/manifest.json", "shapes/inao.parquet"} <= set(zipfile.ZipFile(out).namelist())

    import map_pack
    monkeypatch.setattr(map_pack, "MAP_PACK_URL", str(out))
    client.post("/api/maintenance/map_pack", json={})
    assert wait(client)["result"]["summary"].startswith("No map outlines yet")  # the test store is empty
    client.post("/api/maintenance/map_pack", json={"commit": True})
    job = wait(client)
    assert job["status"] == "done", job["log"]
    assert job["result"]["summary"] == "2 sources installed (2 outlines); 2 appellations and vineyards linked to their outline."
    import geo
    with open(os.path.join(geo.SHAPES_DIR, "manifest.json")) as f:
        assert json.load(f)["vineyard"]["rows"] == 1
    credits = client.get("/api/integrations").json()["map_credits"]
    assert [(c["source"], c["licence"]) for c in credits] == [("inao", "Licence Ouverte 2.0 (Etalab)"),
                                                              ("vineyard", "Licence Ouverte 2.0 (Etalab)")]
    from main import app
    from db import get_session
    session = next(app.dependency_overrides[get_session]())
    assert session.get(Vineyard, 1).boundary == "vineyard:inao-pc:7"  # the premier cru's, not Weinlagen's
    assert session.get(Appellation, 1).boundary == "inao:104"
    # only the display outline ships, and the map draws from it
    import pyarrow.parquet as pq
    schema = pq.read_schema(os.path.join(geo.SHAPES_DIR, "inao.parquet"))
    assert "geometry" not in schema.names and json.loads(schema.metadata[b"geo"])["primary_column"] == "display"
    geom, box = geo.shape("appellation", session.get(Appellation, 1))
    assert json.loads(geom)["type"] == "Polygon" and box == [3, 47, 4, 48]
    session.close()


def test_a_damaged_pack_is_refused(client, tmp_path, monkeypatch):
    out = build_pack(tmp_path)
    damaged = tmp_path / "damaged.zip"
    with zipfile.ZipFile(out) as src, zipfile.ZipFile(damaged, "w") as dst:
        for item in src.infolist():
            data = src.read(item)
            dst.writestr(item, data[:-10] + b"0" * 10 if item.filename.endswith("inao.parquet") else data)
    import map_pack
    monkeypatch.setattr(map_pack, "MAP_PACK_URL", str(damaged))
    client.post("/api/maintenance/map_pack", json={"commit": True})
    job = wait(client)
    assert job["status"] == "failed" and any("checksum" in line for line in job["log"])


def test_a_damaged_pack_leaves_the_store_as_it_was(tmp_path, monkeypatch):
    """One file damaged: nothing swapped in (the good ones neither), no part file left, the manifest unchanged."""
    import geo
    import map_pack
    out = build_pack(tmp_path)
    damaged = tmp_path / "damaged.zip"
    with zipfile.ZipFile(out) as src, zipfile.ZipFile(damaged, "w") as dst:
        names = [i.filename for i in src.infolist() if i.filename.endswith(".parquet")]
        last = sorted(names)[-1]  # a later source damaged: the earlier ones were already checked
        for item in src.infolist():
            data = src.read(item)
            dst.writestr(item, data[:-10] + b"0" * 10 if item.filename == last else data)
    store = tmp_path / "shapes"
    store.mkdir()
    (store / "manifest.json").write_text('{"old": {"file": "old.parquet", "rows": 1}}')
    monkeypatch.setattr(geo, "SHAPES_DIR", str(store))
    import pytest
    with pytest.raises(RuntimeError, match="checksum"):
        map_pack.install(str(damaged), log=lambda *a: None)
    assert sorted(p.name for p in store.iterdir()) == ["manifest.json"]
    assert "old" in (store / "manifest.json").read_text()


def test_a_rebuilt_store_is_read_again(tmp_path, monkeypatch):
    """The manifest rewritten (a rebuild, a pack installed) while the app runs: geo.fresh forgets what it read."""
    import geo
    store = tmp_path / "shapes"
    store.mkdir()
    monkeypatch.setattr(geo, "SHAPES_DIR", str(store))
    (store / "manifest.json").write_text("{}")
    geo.fresh()
    geo._cache["x"] = ("{}", [0, 0, 0, 0])
    geo.fresh()  # nothing changed: kept
    assert "x" in geo._cache
    os.utime(store / "manifest.json", ns=(1, 1))
    geo.fresh()  # rewritten: forgotten
    assert "x" not in geo._cache
