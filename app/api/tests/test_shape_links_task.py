"""Settings › Maintenance › Shape links: app/api/shape_links.py, preview then save."""
import time

from db import Appellation, Region, Vineyard


def seed(s):
    loire, burgundy = Region(name="Loire", country="France"), Region(name="Bourgogne", country="France")
    s.add_all([
        Appellation(name="Chinon", region_obj=loire, inao_id=104),                        # new: links to inao:104
        Appellation(name="Saumur", region_obj=loire, inao_id=999),                        # no shape for it
        Appellation(name="Vouvray", region_obj=loire, inao_id=105, boundary="inao:105"),  # already linked
        Vineyard(name="Les Amoureuses", region_obj=burgundy, vineyard_id=7),              # bourgogne:7
    ])


def write_geo(geo_dir):
    from shapely.geometry import box
    from tests.conftest import local_sources, write_store
    local_sources(geo_dir)  # the bourgogne: vineyard ids are Weinlagen-info's
    write_store(geo_dir, "inao", {"104": box(0, 47, 1, 48), "105": box(1, 47, 2, 48)})
    write_store(geo_dir, "vineyard", {"bourgogne:7": box(4, 47, 4.01, 47.01)}, "vineyard")


from conftest import wait_job as wait  # noqa: E402


def test_preview_then_save(client):
    client.post("/api/maintenance/shape_links", json={})
    job = wait(client)
    assert job["status"] == "done", job
    assert job["result"]["summary"].startswith("2 of 3 appellations linked; 1 of 1 vineyard linked. 2 changes to save"), job
    details = {i["label"]: i["detail"] for i in job["result"]["items"]}
    assert details["Chinon"] == "no outline → inao:104"
    assert details["Les Amoureuses"] == "no outline → vineyard:bourgogne:7"
    assert details["Saumur"].startswith("no shape in the store for inao:999")
    assert client.get("/api/map/regions").json()  # nothing saved yet: Chinon isn't on the map
    assert [r["appellations"] for r in client.get("/api/map/regions").json() if r["name"] == "Loire"] == [1]

    client.post("/api/maintenance/shape_links", json={"commit": True})
    job = wait(client)
    assert job["result"]["summary"].startswith("2 of 3 appellations linked; 1 of 1 vineyard linked. 2 changes saved"), job
    assert [r["appellations"] for r in client.get("/api/map/regions").json() if r["name"] == "Loire"] == [2]
    client.post("/api/maintenance/shape_links", json={})
    assert "0 changes to save" in wait(client)["result"]["summary"]
