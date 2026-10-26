"""The map data pack: geo_scripts/build_map_pack.py packs the sources that may ship (vineyards: INAO's premiers crus
only), Maintenance › Map outlines installs it into an empty store and links the rows, Settings lists the credits."""
import importlib.util
import json
import os
import time
import zipfile

from db import Appellation, Region, Vineyard

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


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
    from shapely.geometry import box
    from tests.conftest import write_store
    store = tmp_path / "pc_geo"
    write_store(str(store), "inao", {"104": box(3, 47, 4, 48)})
    write_store(str(store), "vineyard", {"inao-pc:7": box(4, 47, 4.01, 47.01),       # a premier cru: ships
                                         "bourgogne:7": box(4, 47, 4.02, 47.02)}, "vineyard")  # Weinlagen: doesn't
    spec = importlib.util.spec_from_file_location("build_map_pack", os.path.join(ROOT, "geo_scripts", "build_map_pack.py"))
    build = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build)
    out = tmp_path / "pack.zip"
    pack = build.build(str(store), str(out), log=lambda line: None)
    return out, pack


def test_pack_then_install(client, tmp_path, monkeypatch):
    out, pack = build_pack(tmp_path)
    assert set(pack["sources"]) == {"inao", "vineyard"} and pack["sources"]["vineyard"]["rows"] == 1  # filtered
    assert pack["sources"]["inao"]["licence"].startswith("Licence Ouverte")
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
    out, _ = build_pack(tmp_path)
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
