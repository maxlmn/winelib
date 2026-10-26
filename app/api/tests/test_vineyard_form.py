"""Editing a vineyard (Edit vineyard on its page): name, region, sub-region, village; deleting an unused one."""
from db import Producer, Region, Vineyard, Wine

SQUARE = {"type": "Polygon", "coordinates": [[[4.95, 47.17], [4.96, 47.17], [4.96, 47.18], [4.95, 47.18], [4.95, 47.17]]]}


def seed(s):
    burgundy = Region(name="Bourgogne", country="France")
    used = Vineyard(name="Les Amoureuse", region_obj=burgundy)  # 1: a typo
    s.add_all([Wine(producer=Producer(name="Domaine Roumier"), cuvee="Les Amoureuses", vintage="2019", vineyard=used),
               Vineyard(name="Les Cras", region_obj=burgundy)])  # 2: unused


def test_form_and_rename(client):
    form = client.get("/api/forms/vineyards/1").json()
    assert (form["name"], form["region"]["name"], form["wines"]) == ("Les Amoureuse", "Bourgogne", 1)
    assert client.put("/api/vineyards/1/outline", json={"geometry": SQUARE}).status_code == 200
    r = client.put("/api/vineyards/1", json={"name": "Les Amoureuses", "region": form["region"]["id"],
                                            "sub_region": "Côte de Nuits", "village": "Chambolle-Musigny"})
    assert r.status_code == 200
    v = client.get("/api/vineyards/1").json()
    assert (v["name"], v["subregion"], v["village"]) == ("Les Amoureuses", "Côte de Nuits", "Chambolle-Musigny")
    assert client.get("/api/vineyards/1/outline").json()["custom"]  # the outline stays
    assert client.put("/api/vineyards/1", json={"name": " "}).status_code == 422


def test_delete_only_unused(client):
    assert client.delete("/api/vineyards/1").status_code == 409  # a wine uses it
    assert client.put("/api/vineyards/2/outline", json={"geometry": SQUARE}).status_code == 200
    r = client.delete("/api/vineyards/2")
    assert r.status_code == 200 and r.json()["region"] == "Bourgogne"
    assert client.get("/api/vineyards/2").status_code == 404
