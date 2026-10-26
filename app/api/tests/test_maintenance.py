"""Settings page maintenance: the job runner and its tasks (scripts in app/api/tasks/). No browser, no network."""
import os
import time

import pytest

import jobs
from db import Bottle, Producer, TastingNote, Wine
from conftest import rp_of


def seed(s):
    p = Producer(name="Clos Rougeard")
    a = Wine(producer=p, cuvee="Le Bourg", vintage="2015", type="Red")
    b = Wine(producer=p, cuvee="Le Bourg", vintage="2015", type="Red")  # duplicate of a
    c = Wine(producer=p, cuvee="Les Poyeux", vintage="2016", type="Red")
    d = Wine(producer=p, cuvee="Poyeux", vintage="2017", type="Red")  # similar name to c
    s.add_all([a, b, c, d])
    s.flush()
    dup_bottle = Bottle(wine=b, qty=2, location="H1")
    s.add_all([Bottle(wine=a, qty=1, location="H2"), dup_bottle])
    s.flush()
    s.add(TastingNote(bottle_id=9999, notes="lost"))  # its bottle is gone


def wait(client):
    for _ in range(200):
        job = client.get("/api/maintenance/job").json()
        if job and job["status"] != "running":
            return job
        time.sleep(0.02)
    raise AssertionError("job didn't finish")


@pytest.fixture(autouse=True)
def no_job_left():
    yield
    job = jobs.current()
    if job is not None and job.status == "running":
        job.stop.set()
        job.thread.join(5)


def test_tasks_listed(client):
    tasks = {t["id"]: t for t in client.get("/api/maintenance").json()["tasks"]}
    # the app's own (plug-ins add theirs)
    assert {"duplicates", "orphans", "similar", "similar_producers", "scores_csv", "places", "lwin",
            "prices", "prices_force", "shape_links", "backup"} <= set(tasks)
    assert tasks["duplicates"]["preview"] and tasks["duplicates"]["writes"]
    assert not tasks["orphans"]["writes"]


def test_duplicates_preview_then_merge(client):
    client.post("/api/maintenance/duplicates", json={})
    job = wait(client)
    assert job["status"] == "done" and not job["commit"]
    assert job["result"]["summary"] == "1 group of duplicate wines; merging moves 1 cellar line and deletes 1 emptied duplicate."
    assert client.get("/api/wines/2").json()["cellar"]  # the preview moved nothing

    client.post("/api/maintenance/duplicates", json={"commit": True})
    job = wait(client)
    assert job["status"] == "done" and job["commit"]
    assert sum(b["qty"] for b in client.get("/api/wines/1").json()["cellar"]) == 3  # 1 + the duplicate's 2
    assert client.get("/api/wines/2").status_code == 404  # the emptied duplicate is gone
    # Remembered as the task's last run (saved as the job ends: wait for it)
    jobs.current().thread.join(5)
    last = {t["id"]: t["last"] for t in client.get("/api/maintenance").json()["tasks"]}
    assert last["duplicates"]["status"] == "done" and last["duplicates"]["commit"]
    client.post("/api/maintenance/duplicates", json={})
    assert wait(client)["result"]["summary"].startswith("0 groups")  # nothing left to merge


def test_reports(client):
    client.post("/api/maintenance/orphans", json={})
    job = wait(client)
    assert [i["label"] for i in job["result"]["items"]] == ["Tasting note 1 has no bottle (bottle 9999)"]
    client.post("/api/maintenance/similar", json={})
    job = wait(client)
    (pair,) = job["result"]["items"]
    assert "Les Poyeux" in pair["label"] and "Poyeux" in pair["label"] and pair["href"] == "/producers/1"


def test_backup_and_download(client, tmp_path, monkeypatch):
    import routers.maintenance as m
    monkeypatch.setattr(m, "BACKUP_DIR", str(tmp_path))
    (tmp_path / "winelib_2026-10-20_2047.sql").write_text("-- dump")
    client.post("/api/maintenance/backup", json={})
    job = wait(client)
    assert job["status"] == "done" and any("wines: 3 rows" in line for line in job["log"])  # the duplicate merged away
    listed = client.get("/api/maintenance/backups").json()
    assert {b["kind"] for b in listed} == {"csv", "sql", "sqlite"}  # the test database is SQLite: copied too
    import sqlite3
    copy = next(b for b in listed if b["kind"] == "sqlite")
    with sqlite3.connect(tmp_path / copy["name"]) as c:
        assert c.execute("SELECT COUNT(*) FROM wines").fetchone()[0] == 3
    assert client.get(f"/api/maintenance/backups/{copy['name']}").content[:15] == b"SQLite format 3"
    csv = next(b for b in listed if b["kind"] == "csv")
    z = client.get(f"/api/maintenance/backups/{csv['name']}")
    assert z.headers["content-type"] == "application/zip" and z.content[:2] == b"PK"
    assert client.get("/api/maintenance/backups/winelib_2026-10-20_2047.sql").text == "-- dump"
    assert client.get("/api/maintenance/backups/..%2Fconfig.py").status_code == 404


def test_one_job_at_a_time(client):
    import threading
    gate = threading.Event()

    def slow(session, job):
        gate.wait(5)
    started = jobs.start("slow", "Slow", slow, lambda: type("S", (), {"close": lambda s: None, "rollback": lambda s: None})(),
                         False, {})
    try:
        assert client.post("/api/maintenance/orphans", json={}).status_code == 409
    finally:
        gate.set()
        started.thread.join(5)


def test_unknown_task(client):
    assert client.post("/api/maintenance/nope", json={}).status_code == 404


def test_tasks_say_what_they_need(client, monkeypatch):
    """Without the LWIN list, a price source or a map pack address, those tasks say so instead of failing."""
    import map_pack
    from tasks import bordeaux_index, match_lwin
    from tasks import update_market_prices as prices
    monkeypatch.setattr(match_lwin, "LWIN_DB", "/nonexistent/lwin.sqlite")
    monkeypatch.setattr(bordeaux_index, "configured", lambda: False)
    monkeypatch.setattr(prices, "api_key", lambda: None)
    monkeypatch.setattr(map_pack, "MAP_PACK_URL", "")
    tasks = {t["id"]: t["unavailable"] for t in client.get("/api/maintenance").json()["tasks"]}
    assert "LWIN list" in tasks["lwin"] and "Bordeaux Index" in tasks["prices"] and tasks["prices_force"] == tasks["prices"]
    assert "MAP_PACK_URL" in tasks["map_pack"] and tasks["duplicates"] is None
    monkeypatch.setattr(prices, "api_key", lambda: "key")
    monkeypatch.setattr(map_pack, "MAP_PACK_URL", "https://example.org/pack.zip")
    tasks = {t["id"]: t["unavailable"] for t in client.get("/api/maintenance").json()["tasks"]}
    assert tasks["prices"] is None and tasks["map_pack"] is None
