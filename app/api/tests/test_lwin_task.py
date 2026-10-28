"""Settings › Maintenance › LWIN codes: sure matches saved, doubtful ones only listed."""
import json
import time

import pytest

import jobs
from db import Appellation, Bottle, Producer, Wine
from tests.test_lwin import ENTRIES


def seed(s):
    p = Producer(name="Domaine Jamet")
    cr = Appellation(name="Côte-Rôtie")
    wines = [
        (Wine(producer=p, cuvee="Côte Brune", appellation=cr, vintage="2019", type="Red"), 1),        # 1 exact
        (Wine(producer=p, cuvee="", appellation=cr, vintage="2022", type="Red"), 1),                  # 2 another vintage
        (Wine(producer=p, cuvee="", appellation=cr, vintage="2010", type="Red", lwin="1113824"), 1),  # 3 has one
        (Wine(producer=p, cuvee="Brunes", appellation=cr, vintage="2021", type="Red"), 1),             # 4 doubtful
        (Wine(producer=Producer(name="Nobody"), cuvee="X", vintage="2020", type="Red"), 1),           # 5 none
        (Wine(producer=p, cuvee="Côte Brune", appellation=cr, vintage="2018", type="Red"), 0),        # 6 drunk
    ]
    for w, qty in wines:
        s.add(w)
        s.flush()
        s.add(Bottle(wine_id=w.id, qty=qty, location="H1", price=50, currency="SGD"))


@pytest.fixture
def index(tmp_path, monkeypatch):
    from tasks import match_lwin
    src = tmp_path / "lookup.json"
    entries = ENTRIES["jamet"] + [
        {"lwin": "1999001", "display_name": "Domaine Jamet, Collines Rhodaniennes", "display_name_norm":
         "domaine jamet collines rhodaniennes", "producer_name": "Domaine Jamet", "wine": "Collines Rhodaniennes",
         "wine_norm_light": "collines rhodaniennes", "wine_norm": "collines rhodaniennes", "colour": "Red"}]
    src.write_text(json.dumps({"domaine jamet": entries, "jamet": entries}))
    db = tmp_path / "lwin.sqlite"
    match_lwin.build_index(str(src), str(db))
    monkeypatch.setattr(match_lwin.entries_for, "__defaults__", (str(db),))
    return db


from conftest import wait_job as wait  # noqa: E402


def lwin(client, wid):
    return client.get(f"/api/wines/{wid}").json()["lwin"]


def test_preview_then_run(client, index):
    client.post("/api/maintenance/lwin", json={})
    job = wait(client)
    assert job["result"]["summary"].startswith("4 cellar wines without an LWIN: 2 sure matches"), job["result"]
    assert lwin(client, 1) is None  # a preview saves nothing
    client.post("/api/maintenance/lwin", json={"commit": True})
    job = wait(client)
    jobs.current().thread.join(5)
    assert job["result"]["summary"].startswith("4 cellar wines without an LWIN: 2 saved"), job["log"]
    details = {i["label"]: i["detail"] for i in job["result"]["items"]}
    assert lwin(client, 1) == "1113837" and "(exact)" in details["Domaine Jamet Côte Brune Côte-Rôtie 2019"]
    assert lwin(client, 2) == "1113824" and "another vintage" in details["Domaine Jamet Côte-Rôtie 2022"]
    assert lwin(client, 4) is None and details["Domaine Jamet Brunes Côte-Rôtie 2021"].startswith("To check")
    assert details["Nobody X 2020"] == "No match in the Liv-ex list"
    assert not any("2018" in k for k in details)  # no bottle left in the cellar


def test_without_the_index(client, monkeypatch):
    from tasks import match_lwin
    monkeypatch.setattr(match_lwin.entries_for, "__defaults__", ("/nowhere/lwin.sqlite",))
    client.post("/api/maintenance/lwin", json={})
    job = wait(client)
    assert job["status"] == "failed" and "No LWIN list" in str(job), job
