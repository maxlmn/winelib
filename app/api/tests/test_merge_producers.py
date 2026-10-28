"""Duplicate producers (app/api/tasks/merge_producers.py): the report and the merge."""
import time

import pytest

import jobs
from db import Bottle, Producer, Region, TastingNote, Wine
from conftest import rp, rp_of


def seed(s):
    au = Region(name="Australia", country="Australia")
    a = Producer(name="Place Of Changing Winds", region_obj=au, notes="Macedon.")
    b = Producer(name="Place of Changing Winds", website="https://pocw.example", notes="High density.")
    kept = Wine(producer=a, cuvee="Mount Macedon", vintage="2019", type="Red")
    twin = Wine(producer=b, cuvee="Mount Macedon", vintage="2019", type="Red", scores=rp("96"))
    other = Wine(producer=b, cuvee="Clos de la Colline", vintage="2020", type="Red")
    s.add_all([kept, twin, other,
               Producer(name="Bodegas Vega Sicilia"), Producer(name="Vega Sicilia"),
               Producer(name="Louis Latour"), Producer(name="Chateau Latour")])  # not the same words
    s.flush()
    line = Bottle(wine=twin, qty=2, location="H1")
    s.add_all([Bottle(wine=kept, qty=1, location="H2"), line])
    s.flush()
    s.add(TastingNote(bottle=line, rating=95, notes="Taut"))


from conftest import wait_job as wait  # noqa: E402


@pytest.fixture(autouse=True)
def no_job_left():
    yield
    job = jobs.current()
    if job is not None and job.status == "running":
        job.thread.join(5)


def test_report_offers_the_pairs(client):
    assert "similar_producers" in {t["id"] for t in client.get("/api/maintenance").json()["tasks"]}
    client.post("/api/maintenance/similar_producers", json={})
    items = wait(client)["result"]["items"]
    assert [i["label"] for i in items] == ["“Place Of Changing Winds” / “Place of Changing Winds”",
                                           "“Bodegas Vega Sicilia” / “Vega Sicilia”"]  # most wines first
    assert items[0]["merge"] == {"task": "merge_producers", "a": "Place Of Changing Winds",
                                 "b": "Place of Changing Winds", "wines": [1, 2],
                                 "pick": {"a": {"keep": 1, "drop": 2}, "b": {"keep": 2, "drop": 1}}}
    assert items[0]["detail"] == "Same name"


def test_preview_changes_nothing(client):
    client.post("/api/maintenance/merge_producers", json={"pairs": [{"keep": 1, "drop": 2}]})
    job = wait(client)
    assert job["status"] == "done" and not job["commit"], job["log"]
    assert "1 wine would be moved, 1 wine would be merged" in job["result"]["summary"]
    assert client.get("/api/wines/2").status_code == 200


def test_merge_moves_wines_and_deletes_the_other(client):
    client.post("/api/maintenance/merge_producers", json={"pairs": [{"keep": 1, "drop": 2}], "commit": True})
    job = wait(client)
    assert job["status"] == "done", job["log"]
    assert client.get("/api/wines/2").status_code == 404  # same wine as 1: folded into it
    kept = client.get("/api/wines/1").json()
    assert sorted(b["qty"] for b in kept["cellar"] if b["wine_id"] == 1) == [1, 2]
    assert [t["notes"] for t in kept["tastings"] if t["wine_id"] == 1] == ["Taut"]
    assert rp_of(kept) == "96"
    assert client.get("/api/wines/3").json()["producer"]["id"] == 1
    client.post("/api/maintenance/similar_producers", json={})
    labels = [i["label"] for i in wait(client)["result"]["items"]]
    assert labels == ["“Bodegas Vega Sicilia” / “Vega Sicilia”"]
    client.post("/api/maintenance/orphans", json={})
    assert wait(client)["result"]["summary"].startswith("0 notes without a bottle, 0 bottles without a wine")


def test_details_carried_over(tmp_path):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from db import Base
    from tasks.merge_producers import merge_producer
    engine = create_engine(f"sqlite:///{tmp_path / 'w.db'}")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    seed(s)
    s.commit()
    r = merge_producer(s, 1, 2, log=lambda line: None)
    s.commit()
    p = s.get(Producer, 1)
    assert (p.website, p.notes, r["filled"]) == ("https://pocw.example", "Macedon.\n\nHigh density.", ["website", "notes"])
    assert s.get(Producer, 2) is None
    with pytest.raises(ValueError):
        merge_producer(s, 1, 1)
