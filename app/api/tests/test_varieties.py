"""An appellation's authorized varieties read as the database's grapes (varieties.py): INAO's colour codes dropped,
names found by alias, by the hand-checked list, as a colour mutation, else left unlinked."""
from db import Appellation, Region, Varietal


def seed(s):
    s.add_all([Varietal(name="Cinsault", aliases="Cinsaut, Ottavianello"), Varietal(name="Macabeo", aliases="Macabeu"),
               Varietal(name="Grolleau"), Varietal(name="Jurançon"), Varietal(name="Syrah", aliases="Shiraz"),
               Appellation(name="Bandol", region_obj=Region(name="Provence", country="France"),
                           varieties_text="Cinsaut N, Syrah N, Maccabeu B, Grolleau Gris G, Jurançon Blanc B, "
                                          "Gamay De Bouze N, PDO-FR-A0982, ")])


def test_the_appellation_names_its_grapes(client):
    a = client.get("/api/appellations/1").json()
    assert a["varieties"].startswith("Cinsaut N")  # the register's text, as published
    assert a["grapes"] == [
        {"name": "Cinsaut", "colour": "red", "grape": "Cinsault"},  # an alias
        {"name": "Syrah", "colour": "red", "grape": "Syrah"},
        {"name": "Maccabeu", "colour": "white", "grape": "Macabeo"},  # checked by hand
        {"name": "Grolleau Gris", "colour": "grey", "grape": "Grolleau"},  # a mutation
        {"name": "Jurançon Blanc", "colour": "white", "grape": None},  # a variety of its own
        {"name": "Gamay De Bouze", "colour": "red", "grape": None},  # none in the database
    ]
