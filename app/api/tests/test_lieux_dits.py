"""Lieux-dits for your wines (lieux_dits.py): a cuvée named after a lieu-dit eligible for its appellation is linked to it
as its vineyard, every vintage; a name found in several villages is the user's to choose; a lieu-dit that's only part
of the name isn't one ("Bonnes Blanches" isn't "Les Blanches"). The store is faked: four lieux-dits."""
import json
import time

import numpy as np

import geo
import lieux_dits as ld
from db import Appellation, Producer, Region, Wine

STORE = [  # store id, name, details
    ("49060:le-bourg", "Le Bourg", {"commune_name": "Bellevigne-les-Chateaux", "aocs": "Saumur-Champigny; Saumur", "vines": 0.5}),
    ("49373:le-bourg", "Le Bourg", {"commune_name": "Varrains", "aocs": "Saumur-Champigny; Saumur", "vines": 0.2}),
    ("49060:les-poyeux", "Les Poyeux", {"commune_name": "Bellevigne-les-Chateaux", "aocs": "Saumur-Champigny; Saumur", "vines": 0.9}),
    ("49002:les-blanches", "Les Blanches", {"commune_name": "Allonnes", "aocs": "Anjou", "vines": 0.8}),
]


def fake_store():
    return ([s for s, _, _ in STORE], [n for _, n, _ in STORE], [json.dumps(d) for *_, d in STORE],
            ['{"type":"Point","coordinates":[0,0]}'] * len(STORE), np.zeros((len(STORE), 4)))


def seed(s):
    loire = Region(name="Loire", country="France")
    sc = Appellation(name="Saumur-Champigny", region_obj=loire)
    anjou = Appellation(name="Anjou", region_obj=loire)
    rougeard = Producer(name="Clos Rougeard", region_obj=loire)
    belargus = Producer(name="Domaine Belargus", region_obj=loire)
    s.add_all([loire, sc, anjou, rougeard, belargus,
               Wine(producer=rougeard, cuvee="Le Bourg", vintage="2016", type="Red", appellation=sc, region_obj=loire),
               Wine(producer=rougeard, cuvee="Le Bourg", vintage="2017", type="Red", appellation=sc, region_obj=loire),
               Wine(producer=rougeard, cuvee="Les Poyeux", vintage="2018", type="Red", appellation=sc, region_obj=loire),
               Wine(producer=rougeard, cuvee="Les Poyeux", vintage="2019", type="Red", appellation=sc, region_obj=loire),
               Wine(producer=belargus, cuvee="Bonnes Blanches", vintage="2020", type="White", appellation=anjou, region_obj=loire)])


def test_names_and_spans():
    assert ld.core(ld.words("Les Poyeux")) == ["poyeux"]
    assert ld.span("La Vigne Cendrée", "La Vigne Cendree") == "La Vigne Cendrée"  # the label's accents
    assert ld.span("Clos des Carmes", "Les Carmes") is None and ld.span("Le Bourg", "Le Bourg") == "Le Bourg"
    assert ld._matches(ld.words("Clos des Carmes"), ld.words("Les Carmes"), ["carmes"]) == 1  # the rest is generic
    assert ld._matches(ld.words("Bonnes Blanches"), ld.words("Les Blanches"), ["blanches"]) == 0  # only part of it


def test_preview_pick_and_link(client, monkeypatch):
    monkeypatch.setattr(geo, "_lieux_dits", fake_store)

    def run(**body):
        from conftest import wait_job
        client.post("/api/maintenance/lieux_dits", json=body)
        return wait_job(client)

    job = run(commit=False)
    picks = {it["pick"]["key"].split("=")[1]: it["pick"]["on"] for it in job["result"]["items"]}
    # Les Poyeux: sure; Le Bourg: in two villages, the user's to choose; Bonnes Blanches: not Les Blanches
    assert picks == {"49060:les-poyeux": True, "49060:le-bourg": False, "49373:le-bourg": False}
    keys = [it["pick"]["key"] for it in job["result"]["items"] if it["pick"]["key"].endswith(("les-poyeux", "49060:le-bourg"))]
    job = run(commit=True, keys=keys)
    assert job["status"] == "done", job
    assert "2 cuvées linked" in job["result"]["summary"]

    poyeux = next(r["id"] for r in client.get("/api/search", params={"q": "poyeux 2019"}).json()["results"] if r["kind"] == "wine")
    w = client.get(f"/api/wines/{poyeux}").json()
    assert w["vineyard"]["label"].endswith("Les Poyeux")
    v = client.get(f"/api/vineyards/{w['vineyard']['id']}").json()
    assert (v["name"], v["village"]) == ("Les Poyeux", "Bellevigne-les-Chateaux")
    assert v["lieu_dit"] == {"name": "Les Poyeux", "village": "Bellevigne-les-Chateaux", "aocs": ["Saumur-Champigny", "Saumur"], "vines": 0.9}
    assert len(v["wines"][0]["vintages"]) == 2  # both vintages

    # Linked cuvées aren't offered again
    left = {it["pick"]["key"] for it in run(commit=False)["result"]["items"]}
    assert not any(k.endswith(("les-poyeux", "le-bourg")) for k in left)


def test_from_the_map(client, monkeypatch):
    """A lieu-dit clicked on a wine's map: the wine's vineyard, and its cuvée's other vintages without one."""
    monkeypatch.setattr(geo, "_lieux_dits", fake_store)
    wine = lambda q: next(r["id"] for r in client.get("/api/search", params={"q": q}).json()["results"] if r["kind"] == "wine")  # noqa: E731
    r = client.post(f"/api/wines/{wine('bonnes blanches 2020')}/lieu-dit", json={"lieu_dit": "lieu_dit:49002:les-blanches"})
    assert r.status_code == 200 and r.json()["name"] == "Les Blanches" and r.json()["wines"] == 1
    assert client.get(f"/api/vineyards/{r.json()['vineyard_id']}").json()["lieu_dit"]["village"] == "Allonnes"
    assert client.post(f"/api/wines/{wine('bonnes blanches 2020')}/lieu-dit", json={"lieu_dit": "nowhere"}).status_code == 404


def test_on_a_vineyards_map(client, monkeypatch):
    """A lieu-dit clicked on a vineyard's map: its outline (its wines keep it); not one another vineyard is already."""
    monkeypatch.setattr(geo, "_lieux_dits", fake_store)
    wine = lambda q: next(r["id"] for r in client.get("/api/search", params={"q": q}).json()["results"] if r["kind"] == "wine")  # noqa: E731
    v = client.post(f"/api/wines/{wine('bonnes blanches 2020')}/lieu-dit", json={"lieu_dit": "49002:les-blanches"}).json()["vineyard_id"]
    r = client.post(f"/api/vineyards/{v}/lieu-dit", json={"lieu_dit": "lieu_dit:49060:les-poyeux"})
    assert r.status_code == 200, r.text
    after = client.get(f"/api/vineyards/{v}").json()
    assert after["lieu_dit"]["name"] == "Les Poyeux" and not after["drawn"]
    assert after["name"] == "Les Blanches" and after["village"] == "Allonnes"  # its own name and village stay
    assert len(after["wines"]) == 1
    client.post(f"/api/wines/{wine('le bourg 2016')}/lieu-dit", json={"lieu_dit": "49060:le-bourg"})
    taken = client.post(f"/api/vineyards/{v}/lieu-dit", json={"lieu_dit": "49060:le-bourg"})
    assert taken.status_code == 409 and "Le Bourg" in taken.json()["detail"]
    assert client.post(f"/api/vineyards/{v}/lieu-dit", json={"lieu_dit": "nowhere"}).status_code == 404


def test_in_the_wine_form(client, monkeypatch):
    """The vineyard field finds the store's lieux-dits too; one picked becomes a vineyard when the wine is saved."""
    monkeypatch.setattr(geo, "_lieux_dits", fake_store)
    rows = client.get("/api/lookups/vineyards", params={"q": "bourg"}).json()
    varrains = next(r for r in rows if r.get("ref") == "lieu_dit:49373:le-bourg")
    assert varrains["name"] == "Le Bourg · Varrains (lieu-dit)" and varrains["id"] < 0
    producer = client.get("/api/lookups/producers", params={"q": "rougeard"}).json()[0]["id"]
    r = client.post("/api/wines", json={"producer": producer, "cuvee": "Varrains", "vintage": "2020", "type": "Red",
                                        "vineyard": varrains["ref"]})
    assert r.status_code == 201, r.text
    w = client.get(f"/api/wines/{r.json()['id']}").json()
    assert w["vineyard"]["name"] == "Le Bourg" and "Varrains" in w["vineyard"]["label"]
    # now a vineyard: found as one, no longer offered as a lieu-dit
    again = client.get("/api/lookups/vineyards", params={"q": "bourg"}).json()
    assert not any(x.get("ref") == "lieu_dit:49373:le-bourg" for x in again)


def test_plurals():
    """A label's plural is the cadastre's singular, and back"""
    from lieux_dits import _matches, span, words, core
    name = words("Chétillon")
    assert _matches(words("Les Chétillons"), name, core(name)) == 2
    assert span("Cuvée Les Chétillons", "Chetillon") == "Chétillons"
    name = words("Les Noues")
    assert _matches(words("La Noue"), name, core(name)) == 1


def test_suggestion_on_its_map(client, monkeypatch):
    """A suggestion's map before it's linked: the wine's appellation, the lieu-dit as its vineyard."""
    monkeypatch.setattr(geo, "_lieux_dits", fake_store)
    wine = next(r["id"] for r in client.get("/api/search", params={"q": "bonnes blanches 2020"}).json()["results"] if r["kind"] == "wine")
    r = client.get(f"/api/wines/{wine}/shapes", params={"lieu_dit": "49002:les-blanches"})
    assert r.status_code == 200, r.text
    vines = r.json()["vineyards"]["features"]
    assert [f["properties"]["name"] for f in vines] == ["Les Blanches"] and vines[0]["properties"]["village"] == "Allonnes"
    assert client.get(f"/api/wines/{wine}/shapes", params={"lieu_dit": "nowhere"}).status_code == 404
