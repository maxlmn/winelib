"""Editing an appellation, and deleting one no wine uses (Himmalaya, a typo); one still in use is refused."""
from db import Appellation, Producer, Region, Wine


def seed(s):
    china = Region(name="China", country="China")
    used = Appellation(name="Ningxia", region_obj=china)
    s.add_all([Appellation(name="Himmalaya", region_obj=china),
               Wine(producer=Producer(name="Celebre"), vintage="2018", type="Red", appellation=used)])


def test_unused_appellation_can_be_deleted(client):
    assert client.get("/api/forms/appellations/1").json()["wines"] == 0
    assert client.delete("/api/appellations/1").json() == {"deleted": 1, "region": "China"}
    assert client.get("/api/appellations/1").status_code == 404


def test_appellation_in_use_is_kept(client):
    assert client.get("/api/forms/appellations/2").json()["wines"] == 1
    r = client.delete("/api/appellations/2")
    assert r.status_code == 409 and "still has 1 wine" in r.text


def test_appellation_edit(client):
    form = client.get("/api/forms/appellations/2").json()
    assert form["name"] == "Ningxia" and form["region"]["name"] == "China" and form["wines"] == 1
    body = {"name": "Ningxia Helan Mountain", "region": form["region"]["id"], "type": "GI", "colors": "Red"}
    assert client.put("/api/appellations/2", json=body).json() == {"id": 2}
    a = client.get("/api/appellations/2").json()
    assert (a["name"], a["region"], a["type"], a["colors"]) == ("Ningxia Helan Mountain", "China", "GI", "Red")
    # a new region, by name
    assert client.put("/api/appellations/2", json={**body, "region": {"name": "Ningxia"}}).status_code == 200
    assert client.get("/api/appellations/2").json()["region"] == "Ningxia"
