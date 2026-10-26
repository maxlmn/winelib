"""GET /api/export.json and /api/export.zip: every table, to take elsewhere."""
import csv
import io
import zipfile
from datetime import date

from db import Bottle, CriticScore, Producer, Region, TastingNote, Wine


def seed(s):
    loire = Region(name="Loire")
    w = Wine(producer=Producer(name="Clos Rougeard", region_obj=loire), cuvee="Le Bourg", vintage="2016", type="Red")
    w.scores.append(CriticScore(critic="Vinous", score="95", note="Dense."))
    b = Bottle(wine=w, qty=2, location="H1", price=120, currency="EUR", purchase_date=date(2024, 3, 1))
    s.add_all([b, TastingNote(bottle=b, date=date(2025, 1, 2), rating=95, notes="Superb.")])


def test_json(client):
    r = client.get("/api/export.json")
    assert r.headers["content-disposition"].startswith('attachment; filename="winelib_export_')
    body = r.json()
    assert (body["format"], body["version"]) == ("winelib", 1)
    t = body["tables"]
    assert [s["critic"] for s in t["critic_scores"]] == ["Vinous"]
    assert t["cellar"][0]["purchase_date"] == "2024-03-01" and t["tasting_notes"][0]["notes"] == "Superb."
    assert len(t["app_settings"]) == 1 and list(t).index("producers") > list(t).index("regions")  # dependency order


def test_zip(client):
    z = zipfile.ZipFile(io.BytesIO(client.get("/api/export.zip").content))
    assert {"wines.csv", "critic_scores.csv", "cellar.csv", "tasting_notes.csv", "app_settings.csv"} <= set(z.namelist())
    rows = list(csv.DictReader(io.StringIO(z.read("wines.csv").decode())))
    assert (rows[0]["cuvee"], rows[0]["vintage"]) == ("Le Bourg", "2016")


def test_restore_round_trip(client, tmp_path):
    """scripts/restore_export.py: the export rebuilds a new database, the same rows; refused on one with data."""
    import importlib.util
    import os
    import pytest
    from sqlalchemy import create_engine
    import migrate
    path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "scripts", "restore_export.py")
    spec = importlib.util.spec_from_file_location("restore_export", path)
    restore = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(restore)
    export = client.get("/api/export.json").json()
    engine = create_engine(f"sqlite:///{tmp_path / 'new.db'}")
    migrate.upgrade(engine)
    counts = restore.restore(engine, export)
    assert counts["wines"] == 1 and counts["critic_scores"] == 1 and counts["app_settings"] == 1
    with engine.connect() as c:
        from sqlalchemy import text
        assert c.execute(text("SELECT purchase_date FROM cellar")).scalar() in ("2024-03-01", __import__("datetime").date(2024, 3, 1))
    with pytest.raises(SystemExit):
        restore.restore(engine, export)  # it has rows now
