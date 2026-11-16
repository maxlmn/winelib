"""Duplicate wines (Settings › Maintenance): a cuvée spelled with other capitals or dashes is the same cuvée."""

from conftest import wait_job as wait
from db import Bottle, Producer, Wine
from tasks.consolidate_duplicate_wines import fold_name


def seed(s):
    p = Producer(name="Domaine Armand Rousseau")
    a = Wine(producer=p, cuvee="Clos-de-Bèze", vintage="2015", type="Red")
    b = Wine(producer=p, cuvee="clos de  Bèze", vintage="2015", type="Red")
    c = Wine(producer=p, cuvee="Clos de Bèze", vintage="2016", type="Red")  # another vintage: another wine
    s.add_all([a, b, c])
    s.flush()
    s.add_all([Bottle(wine=a, qty=1, location="H1"), Bottle(wine=b, qty=2, location="H2")])


def test_fold_name():
    assert fold_name("Clos-de-Bèze") == fold_name("clos de  bèze") == fold_name("CLOS – DE – BÈZE") == "clos de bèze"
    assert fold_name(None) == fold_name("") == ""


def test_spellings_found_and_merged(client):
    client.post("/api/maintenance/duplicates", json={})
    job = wait(client)
    assert job["status"] == "done"
    [group] = job["result"]["items"]
    assert [c["href"] for c in group["copies"]] == ["/wines/1", "/wines/2"]
    client.post("/api/maintenance/duplicates", json={"commit": True})
    assert wait(client)["status"] == "done"
    assert sum(b["qty"] for b in client.get("/api/wines/1").json()["cellar"]) == 3
    assert client.get("/api/wines/2").status_code == 404
    assert client.get("/api/wines/3").status_code == 200
