"""reference.py: a new, empty database gets the reference data (app/api/data/reference/*.csv); one with regions doesn't."""
from sqlalchemy import create_engine, text

import migrate
import reference
from db import Region
from sqlalchemy.orm import Session


def write(folder):
    (folder / "regions.csv").write_text(encoding="utf-8", data="id,name,country,color,iso_code\n3,Loire,France,#a00,FR\n7,Rhône,France,,FR\n")
    (folder / "appellations.csv").write_text(encoding="utf-8", data="id,name,region_id,aliases,max_yield_hl\n10,Hermitage,7,Ermitage,40.0\n"
                                             "11,Saumur-Champigny,3,,\n")
    (folder / "varietals.csv").write_text(encoding="utf-8", data="id,name,aliases,unknown_column\n1,Syrah,Shiraz,x\n")
    (folder / "producers.csv").write_text(encoding="utf-8", data="id,name,aliases,region_id,village,notes\n"
                                          "4,Domaine Jamet,Jamet,7,Ampuis,mine\n")
    (folder / "vineyards.csv").write_text(encoding="utf-8", data="id,vineyard_id,name,region_id,boundary\n5,77,Les Bessards,7,vineyard:rhone:77\n"
                                          "6,,Drawn by hand,3,custom:12\n")


def test_an_empty_database_gets_it_once(tmp_path, monkeypatch):
    write(tmp_path)
    monkeypatch.setattr(reference, "REFERENCE_DIR", str(tmp_path))
    engine = create_engine(f"sqlite:///{tmp_path / 'new.db'}")
    migrate.upgrade(engine)
    assert reference.seed(engine) == {"regions": 2, "appellations": 2, "varietals": 1, "vineyards": 2, "producers": 1}
    with engine.connect() as c:
        assert c.execute(text("SELECT name, aliases, max_yield_hl FROM appellations WHERE id = 10")).one() == (
            "Hermitage", "Ermitage", 40.0)
        assert c.execute(text("SELECT boundary FROM vineyards ORDER BY id")).scalars().all() == ["vineyard:rhone:77", None]
    with Session(engine) as s:  # the next region follows the file's ids
        s.add(Region(name="Alsace"))
        s.commit()
        assert s.query(Region.id).filter_by(name="Alsace").scalar() == 8
    assert reference.seed(engine) == {}  # it has regions now: left alone


def rows_of(engine, sql):
    with engine.connect() as c:
        return c.execute(text(sql)).all()


def test_updates_add_what_is_new_and_fill_what_is_empty(tmp_path, monkeypatch):
    """A newer version's reference data, by stable key: new rows added (under this database's region ids), empty
    fields filled, nothing overwritten, nothing deleted or renamed here brought back; a rerun changes nothing."""
    write(tmp_path)
    monkeypatch.setattr(reference, "REFERENCE_DIR", str(tmp_path))
    engine = create_engine(f"sqlite:///{tmp_path / 'db.db'}")
    migrate.upgrade(engine)
    reference.seed(engine)
    assert reference.update(engine) == {"baseline": True}  # keys recorded, nothing changed
    assert rows_of(engine, "SELECT COUNT(*) FROM reference_keys")[0][0] == 2 + 2 + 1 + 2 + 1
    with engine.begin() as c:  # the user's own changes
        c.execute(text("DELETE FROM varietals WHERE name = 'Syrah'"))
        c.execute(text("UPDATE appellations SET name = 'Saumur Champigny (mine)' WHERE name = 'Saumur-Champigny'"))
        c.execute(text("UPDATE appellations SET max_yield_hl = 45 WHERE name = 'Hermitage'"))
    # The next version: other ids, a new region and appellations, more fields
    (tmp_path / "regions.csv").write_text(encoding="utf-8", data="id,name,country,color,iso_code\n30,Loire,France,#a00,FR\n70,Rhône,France,,FR\n"
                                          "80,Jura,France,#ff0,FR\n")
    (tmp_path / "appellations.csv").write_text(encoding="utf-8", data=
        "id,name,region_id,aliases,max_yield_hl,category\n"
        "100,Hermitage,70,Ermitage,40.0,Wine\n"            # max yield edited here (45): kept; category: filled
        "101,Saumur-Champigny,30,,50,\n"                   # renamed here: not brought back
        "102,Crozes-Hermitage,70,,45,Wine\n"               # new
        "103,Château-Chalon,80,,,Wine\n")                  # new, in a new region
    (tmp_path / "varietals.csv").write_text(encoding="utf-8", data="id,name,aliases\n1,Syrah,Shiraz\n2,Savagnin,Traminer\n")
    (tmp_path / "producers.csv").write_text(encoding="utf-8", data="id,name,aliases,region_id,village,winemaker\n"
                                            "9,Domaine Jamet,Jamet,70,Ampuis,Jean-Paul Jamet\n"  # winemaker: filled
                                            "10,Domaine Macle,,80,Château-Chalon,\n")          # new, in the new region
    report = reference.update(engine)
    assert report["regions"]["added"] == 1 and report["appellations"]["added"] == 2 and report["varietals"]["added"] == 1
    assert rows_of(engine, "SELECT a.name, r.name, a.max_yield_hl, a.category FROM appellations a "
                           "JOIN regions r ON r.id = a.region_id ORDER BY a.name") == [
        ("Château-Chalon", "Jura", None, "Wine"), ("Crozes-Hermitage", "Rhône", 45.0, "Wine"),
        ("Hermitage", "Rhône", 45.0, "Wine"), ("Saumur Champigny (mine)", "Loire", None, None)]
    assert [n for (n,) in rows_of(engine, "SELECT name FROM varietals")] == ["Savagnin"]  # Syrah stays deleted
    assert rows_of(engine, "SELECT p.name, r.name, p.winemaker FROM producers p JOIN regions r ON r.id = p.region_id "
                           "ORDER BY p.name") == [("Domaine Jamet", "Rhône", "Jean-Paul Jamet"),
                                                  ("Domaine Macle", "Jura", None)]
    assert rows_of(engine, "SELECT notes FROM producers WHERE name = 'Domaine Jamet'") == [(None,)]  # not reference data
    assert reference.update(engine) == {t: {"added": 0, "filled": 0, "skipped": 0}
                                        for t in ("regions", "appellations", "varietals", "vineyards", "producers")}


def test_found_by_alias_and_any_script(tmp_path, monkeypatch):
    """A row is found by its name or an alias (Ermitage for Hermitage), accents and case aside, in any script."""
    assert reference.norm("Malvasia Σητείας") == "malvasia σητειασ" and reference.norm("Côte-Rôtie") == "cote rotie"
    write(tmp_path)
    monkeypatch.setattr(reference, "REFERENCE_DIR", str(tmp_path))
    engine = create_engine(f"sqlite:///{tmp_path / 'db.db'}")
    migrate.upgrade(engine)
    with engine.begin() as c:  # an installation from before, which calls it Ermitage
        c.execute(text("INSERT INTO regions (id, name, country) VALUES (1, 'Rhône', 'France')"))
        c.execute(text("INSERT INTO appellations (id, name, region_id) VALUES (1, 'ERMITAGE', 1)"))
        c.execute(text("INSERT INTO reference_keys (table_name, key) VALUES ('regions', 'rhone')"))
    report = reference.update(engine)
    assert report["appellations"] == {"added": 1, "filled": 1, "skipped": 0}  # Saumur-Champigny's region: added too
    assert rows_of(engine, "SELECT name, aliases, max_yield_hl FROM appellations WHERE id = 1") == [("ERMITAGE", "Ermitage", 40.0)]
