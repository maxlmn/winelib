"""A vineyard set on a wine goes to its other vintages. Run from app/api:  pytest"""
from db import Appellation, Producer, Region, Varietal, Vineyard, Wine

import db
from main import app

IDS = {}


def seed(s):
    loire = Region(name="Loire")
    chinon = Appellation(name="Chinon", region_obj=loire)
    cf = Varietal(name="Cabernet Franc")
    coulaine = Producer(name="Chateau de Coulaine", region_obj=loire)
    picasses, clos, haut = (Vineyard(name=n, region_obj=loire) for n in ("Les Picasses", "Les Clos", "Picasses Haut"))

    def vintage(year, cuvee="Les Picasses", vineyard=None):
        return Wine(producer=coulaine, cuvee=cuvee, vintage=year, type="Red", region_obj=loire, appellation=chinon,
                    varietal=cf, vineyard=vineyard)

    wines = dict(w2020=vintage("2020", vineyard=picasses), w2019=vintage("2019"), w2018=vintage("2018", vineyard=clos),
                 other_cuvee=vintage("2019", cuvee="Autre"))
    s.add_all(wines.values())
    s.flush()
    IDS.update({k: w.id for k, w in wines.items()}, loire=loire.id, chinon=chinon.id, cf=cf.id, coulaine=coulaine.id,
               picasses=picasses.id, clos=clos.id, haut=haut.id)


def put(client, vineyard):
    return client.put(f"/api/wines/{IDS['w2020']}", json={
        "producer": IDS["coulaine"], "cuvee": "Les Picasses", "vintage": "2020", "type": "Red", "region": IDS["loire"],
        "appellation": IDS["chinon"], "varietal": IDS["cf"], "vineyard": vineyard})


def vineyards():
    s = next(app.dependency_overrides[db.get_session]())
    return [s.get(Wine, IDS[k]).vineyard_id for k in ("w2019", "w2018", "other_cuvee")]


def test_vineyard_goes_to_the_other_vintages(client):
    """Same producer, cuvée, appellation and grape: a vintage without a vineyard (or with the old one) gets it; one
    with another vineyard keeps it; another cuvée is left alone; an unchanged vineyard touches nothing."""
    assert put(client, IDS["picasses"]).json()["vintages_updated"] == 0
    assert vineyards() == [None, IDS["clos"], None]
    assert put(client, IDS["haut"]).json()["vintages_updated"] == 1
    assert vineyards() == [IDS["haut"], IDS["clos"], None]
    assert put(client, IDS["picasses"]).json()["vintages_updated"] == 1  # the 2019 had the same one: it follows
    assert vineyards() == [IDS["picasses"], IDS["clos"], None]


def test_a_new_vintage_takes_the_vineyard_its_other_vintages_share(client):
    """A new wine without a vineyard takes its other vintages' when they all have the same one (the wine form, a
    bottle of a new wine); none when they differ or have none; one given is kept."""
    def new(cuvee, year, path="/api/wines", **extra):
        wine = {"producer": IDS["coulaine"], "cuvee": cuvee, "vintage": year, "type": "Red", "region": IDS["loire"],
                "appellation": IDS["chinon"], "varietal": IDS["cf"], **extra}
        r = client.post(path, json=wine if path == "/api/wines" else {"wine": wine, "qty": 1, "location": "R1"})
        assert r.status_code == 201, r.text
        s = next(app.dependency_overrides[db.get_session]())
        wid = r.json()["id"] if path == "/api/wines" else r.json()["wine_id"]
        return s.get(Wine, wid).vineyard_id

    assert new("Les Picasses", "2021") is None  # its vintages disagree (Les Picasses, Les Clos)
    assert new("Autre", "2021") is None  # none has one
    s = next(app.dependency_overrides[db.get_session]())
    s.get(Wine, IDS["other_cuvee"]).vineyard_id = IDS["haut"]
    s.commit()
    assert new("Autre", "2022", path="/api/bottles") == IDS["haut"]  # Autre 2019 and 2021: one between them
    assert new("Autre", "2023", vineyard=IDS["clos"]) == IDS["clos"]  # given: kept
