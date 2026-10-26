"""Sparkling rosés: a Bubbles wine named as a rosé ("Brut Rosé") is saved as Bubbles Rose, by the wine form and the
cellar import (the one-off Maintenance task that moved the old ones is gone)."""
from db import Producer, Wine


def seed(s):
    p = Producer(name="Billecart-Salmon")
    s.add_all([Wine(producer=p, cuvee="Brut Rosé", vintage="NV", type="Bubbles"),
               Wine(producer=p, cuvee="Elisabeth Salmon Rose", vintage="2012", type="Bubbles"),
               Wine(producer=p, cuvee="Clos des Roses", vintage="2008", type="Bubbles"),  # not a rosé
               Wine(producer=p, cuvee="Brut Réserve", vintage="NV", type="Bubbles"),
               Wine(producer=p, cuvee="Rosé", vintage="2020", type="Rose")])  # still


def test_form_saves_a_named_rose_as_one(client):
    form = {"producer": 1, "cuvee": "Brut Rosé", "vintage": "NV", "type": "Bubbles"}
    assert client.put("/api/wines/1", json=form).status_code == 200
    assert client.get("/api/wines/1").json()["color"] == "Bubbles Rose"
    assert client.put("/api/wines/3", json={**form, "cuvee": "Clos des Roses", "vintage": "2008"}).status_code == 200
    assert client.get("/api/wines/3").json()["color"] == "Bubbles"  # not a rosé


def test_import_reads_a_named_rose(client):
    from tasks.import_cellar import colour_of, plan
    from db import get_session
    from main import app
    s = next(app.dependency_overrides[get_session]())
    rows = [{"Producer": "Billecart-Salmon", "Wine": "Brut Rosé", "Vintage": "2015", "Color": "Sparkling"}]
    (item,) = plan(s, rows, {"producer": "Producer", "cuvee": "Wine", "vintage": "Vintage", "colour": "Color"})
    assert item["colour"] == "Bubbles Rose"
    s.close()


def test_form_offers_it(client):
    assert "Bubbles Rose" in client.get("/api/lookups/options").json()["wine_types"]
