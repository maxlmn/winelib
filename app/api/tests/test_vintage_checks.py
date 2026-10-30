"""A cuvée's vintages checked against each other (tasks/vintages.py, Settings › Maintenance): cuvées under several
appellations reported. Run from app/api:  pytest"""
from conftest import wait_job as wait
from db import Appellation, Producer, Region, Vineyard, Wine


def seed(s):
    burgundy = Region(name="Bourgogne")
    vdf, hcdn, hcdb = (Appellation(name=n, region_obj=burgundy) for n in
                       ("Vin de France", "Bourgogne Hautes-Côtes de Nuits", "Bourgogne Hautes-Côtes de Beaune"))
    krug, other = Producer(name="Maison Valentin Krug"), Producer(name="Domaine Autre")
    battois, vermots = Vineyard(name="Mont Battois", region_obj=burgundy), Vineyard(name="Dessus les Vermots")
    s.add_all([
        # Marcelle: two vintages on Dessus les Vermots, one without -> given it
        Wine(producer=krug, cuvee="Marcelle", vintage="2020", type="Red", appellation=vdf, vineyard=vermots),
        Wine(producer=krug, cuvee="Marcelle", vintage="2021", type="Red", appellation=vdf, vineyard=vermots),
        Wine(producer=krug, cuvee="Marcelle", vintage="2022", type="Red", appellation=vdf),
        # Hautes-Sphères: its vintages disagree on the vineyard (none given); 2021 under two appellations
        Wine(producer=krug, cuvee="Hautes-Spheres", vintage="2020", type="Red", appellation=vdf, vineyard=battois),
        Wine(producer=krug, cuvee="Hautes-Spheres", vintage="2021", type="Red", appellation=vdf, vineyard=vermots),
        Wine(producer=krug, cuvee="Hautes-Spheres", vintage="2019", type="Red", appellation=vdf),
        Wine(producer=krug, cuvee="Hautes-Spheres", vintage="2021", type="Red", appellation=hcdn),
        Wine(producer=krug, cuvee="Hautes-Spheres", vintage="2023", type="Red", appellation=hcdb),
        # another producer's cuvée of the same name: apart
        Wine(producer=other, cuvee="Marcelle", vintage="2022", type="Red", appellation=hcdn),
    ])


def test_appellations_apart(client):
    client.post("/api/maintenance/appellations_apart", json={})
    job = wait(client)
    assert job["status"] == "done", job
    items = job["result"]["items"]
    assert len(items) == 1 and items[0]["label"] == "Maison Valentin Krug Hautes-Spheres (under two: 2021)"
    assert items[0]["detail"] == ("Bourgogne Hautes-Côtes de Beaune: 2023 · Bourgogne Hautes-Côtes de Nuits: 2021 · "
                                  "Vin de France: 2019, 2020, 2021")
