"""Shape links (app/api/shape_links.py, and geo_scripts/link_shapes.py printing its report): the boundary column,
filled from shape_sources.json's link rules and the store."""
import importlib.util
import os

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "geo_scripts", f"{name}.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def link():
    """The PC's command (main), the app's module (names_match) and build_shapes (to write a store)."""
    from types import SimpleNamespace
    import shape_links
    return SimpleNamespace(main=load("link_shapes").main, names_match=shape_links.names_match,
                           build_shapes=load("build_shapes"))


@pytest.fixture
def setup(tmp_path, link):
    """A database like the app's (no boundary column yet) and a store with a few shapes per source."""
    from shapely.geometry import box
    from winelib_utils.models import Appellation, Base, Region, Vineyard
    url = f"sqlite:///{tmp_path / 'wine.db'}"
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    fr, it, us, au, es = (Region(name=n, country=c) for n, c in (("Loire", "France"), ("Piemonte", "Italy"),
                          ("California", "United States"), ("Australia", "Australia"), ("Rioja", "Spain")))
    burgundy, pfalz = Region(name="Burgundy", country="France"), Region(name="Pfalz", country="Germany")
    s.add_all([
        Appellation(name="Chinon", region_obj=fr, inao_id=101),                            # inao
        Appellation(name="Saumur", region_obj=fr, inao_id=999, pdo_id="PDO-FR-A0001"),     # no INAO shape: EU
        Appellation(name="Barolo", region_obj=it, pdo_id="PDO-IT-A1234"),                  # eu
        Appellation(name="Napa Valley", region_obj=us, pdo_id="US-AVA-napa_valley"),       # ava
        Appellation(name="Ghost", region_obj=fr, inao_id=555),                             # no shape anywhere
        Appellation(name="McLaren Valley", region_obj=au),                                 # au, by alias
        Appellation(name="Rioja", region_obj=es),                                          # nothing to link by
        Vineyard(name="Les Amoureuses", region_obj=burgundy, vineyard_id=7),   # 7 in both files: the premier cru
        Vineyard(name="Clos Blanc", region_obj=burgundy, vineyard_id=7),       # 7 in both, neither its name: ambiguous
        Vineyard(name="Les Genevrières", region_obj=burgundy, vineyard_id=9),  # only in Weinlagen's file
        Vineyard(name="Kirchenstück", region_obj=pfalz, vineyard_id=7),        # pfalz:7
        Vineyard(name="Pechstein", region_obj=pfalz, vineyard_id=8),           # pfalz:8 is Jesuitengarten: to check
        Vineyard(name="Lost", region_obj=pfalz, vineyard_id=99),               # no shape
    ])
    s.commit()
    s.close()
    geo = tmp_path / "geo"
    b = box(0, 0, 1, 1).wkb
    build = link.build_shapes
    from tests.conftest import local_sources
    local_sources(str(geo))  # Weinlagen-info's vineyard files, as on the PC
    for source, ids, kind in (("inao", ["101"], "appellation"), ("eu", ["PDO-FR-A0001", "PDO-IT-A1234"], "appellation"),
                              ("ava", ["napa_valley"], "appellation"), ("au", ["mclaren-vale"], "appellation")):
        build.write(str(geo / "shapes"), source, [(i, None, None, b) for i in ids], kind)
    build.write(str(geo / "shapes"), "vineyard", [(i, n, None, b) for i, n in (
        ("bourgogne:7", "Clos de Vougeot"), ("inao-pc:7", "Les Amoureuses"), ("bourgogne:9", "Genevrières"),
        ("pfalz:7", "Kirchenstück"), ("pfalz:8", "Jesuitengarten"))], "vineyard")
    return str(geo), url, engine


def boundaries(engine, table):
    with engine.connect() as c:
        return dict(c.execute(text(f"SELECT name, boundary FROM {table}")).fetchall())


def test_dry_run_reports_and_saves_nothing(setup, link, capsys):
    geo, url, engine = setup
    link.main(geo, url)
    out = capsys.readouterr().out
    assert set(boundaries(engine, "appellations").values()) == {None}  # nothing saved
    assert "linked to inao: 1" in out and "linked to eu: 2" in out and "linked to ava: 1" in out and "linked to au: 1" in out
    assert "Ghost (Loire, France): no inao:555" in out
    assert "nothing to link by (no id, not a linked country): 1" in out  # Rioja
    assert "linked to vineyard: 4" in out and "Lost (Pfalz, Germany): no vineyard:pfalz:99" in out
    assert "ambiguous (their id is in several files, none or several with their name): 1" in out
    assert "Clos Blanc (Burgundy): vineyard:bourgogne:7 (Clos de Vougeot) or vineyard:inao-pc:7 (Les Amoureuses)" in out
    assert "Pechstein (Pfalz) -> vineyard:pfalz:8, named Jesuitengarten" in out


def test_commit_links_and_a_rerun_changes_nothing(setup, link, capsys):
    geo, url, engine = setup
    link.main(geo, url, commit=True)
    assert boundaries(engine, "appellations") == {
        "Chinon": "inao:101", "Saumur": "eu:PDO-FR-A0001", "Barolo": "eu:PDO-IT-A1234", "Napa Valley": "ava:napa_valley",
        "Ghost": None, "McLaren Valley": "au:mclaren-vale", "Rioja": None}
    assert boundaries(engine, "vineyards") == {
        "Les Amoureuses": "vineyard:inao-pc:7", "Clos Blanc": None, "Les Genevrières": "vineyard:bourgogne:9",
        "Kirchenstück": "vineyard:pfalz:7", "Pechstein": "vineyard:pfalz:8", "Lost": None}
    capsys.readouterr()
    link.main(geo, url, commit=True)
    assert capsys.readouterr().out.count("changes: 0") == 2


def test_links_survive_a_machine_without_the_local_sources(setup, link):
    """Run where sources.local.json is missing (a machine not set up yet), the Weinlagen-info links stay: no rule finds
    them another shape and theirs is still in the store."""
    geo, url, engine = setup
    link.main(geo, url, commit=True)
    before = boundaries(engine, "vineyards")
    os.remove(os.path.join(geo, "sources.local.json"))
    link.main(geo, url, commit=True)
    after = boundaries(engine, "vineyards")
    assert {n: b for n, b in before.items() if b} == {n: after[n] for n, b in before.items() if b}


def test_a_link_set_by_hand_is_kept_and_a_gone_shape_unlinked(setup, link):
    geo, url, engine = setup
    link.main(geo, url, commit=True)
    with engine.begin() as c:
        c.execute(text("UPDATE appellations SET boundary = 'custom:1' WHERE name = 'Rioja'"))
    from shapely.geometry import box
    link.build_shapes.write(os.path.join(geo, "shapes"), "inao", [("102", "x", None, box(0, 0, 1, 1).wkb)],
                            "appellation")  # rebuilt without 101
    link.main(geo, url, commit=True)
    found = boundaries(engine, "appellations")
    assert found["Rioja"] == "custom:1"
    assert found["Chinon"] is None  # its INAO shape is gone, and it has no other id


def test_eu_by_name_when_there_is_no_pdo_id(tmp_path, link):
    """An appellation without pdo_id finds its EU shape by the shape's name in its country, or by an alias."""
    from shapely.geometry import box
    from winelib_utils.models import Appellation, Base, Region
    url = f"sqlite:///{tmp_path / 'wine.db'}"
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    es, it, fr = Region(name="Castilla", country="Spain"), Region(name="Umbria", country="Italy"), Region(name="Provence", country="France")
    s.add_all([
        Appellation(name="Ribera del Duero", region_obj=es),                         # exact name
        Appellation(name="Sagrantino di Montefalco", region_obj=it),                 # alias in shape_sources.json
        Appellation(name="Bellet", region_obj=fr),                                    # one of "Bellet / Vin de Bellet"
        Appellation(name="Collio Goriziano (Collio)", region_obj=it),                # the whole "Collio Goriziano / Collio"
        Appellation(name="Rioja", region_obj=es, pdo_id="PDO-ES-A0117"),              # has its id: by id only
        Appellation(name="León", region_obj=it),                                      # a Spanish name, in Italy
        Appellation(name="Castilla y León", region_obj=es),                          # a PGI: no PDO shape
    ])
    s.commit()
    s.close()
    geo = tmp_path / "geo"
    b = box(0, 0, 1, 1).wkb
    link.build_shapes.write(str(geo / "shapes"), "eu", [
        ("PDO-ES-A0626", "Ribera del Duero", None, b), ("PDO-IT-A0833", "Montefalco Sagrantino", None, b),
        ("PDO-FR-A0663", "Bellet / Vin de Bellet", None, b), ("PDO-ES-A0117", "Rioja", None, b),
        ("PDO-IT-A0908", "Collio Goriziano / Collio", None, b),
        ("PDO-ES-A0882", "León", None, b)], "appellation")
    link.main(str(geo), url, commit=True)
    with engine.connect() as c:
        found = c.execute(text("SELECT a.name, r.country, a.boundary FROM appellations a JOIN regions r ON r.id = a.region_id")).fetchall()
    assert {(n, c, b) for n, c, b in found} == {
        ("Ribera del Duero", "Spain", "eu:PDO-ES-A0626"), ("Sagrantino di Montefalco", "Italy", "eu:PDO-IT-A0833"),
        ("Bellet", "France", "eu:PDO-FR-A0663"), ("Rioja", "Spain", "eu:PDO-ES-A0117"),
        ("Collio Goriziano (Collio)", "Italy", "eu:PDO-IT-A0908"),
        ("León", "Italy", None), ("Castilla y León", "Spain", None)}


def test_names_match_in_any_script_and_across_dashes(link):
    assert link.names_match("Сакар", "Сакар") and link.names_match("Σαντορίνη", "Σαντορίνη")
    assert link.names_match("Big Valley District–Lake County", "Big Valley District-Lake County")
    assert link.names_match("Montepulciano d'Abruzzo", "Montepulciano d’Abruzzo")
    assert link.names_match("Amoureuses", "Les Amoureuses")
    assert not link.names_match("Pommard Les Cras", "Fixin premier cru Les Meix Bas")
    assert not link.names_match("Santorini", "Σαντορίνη")  # another script: listed, to check by eye


def test_admin_areas_by_country_and_name(tmp_path, link):
    """An appellation that is an administrative area (Toscana IGT, Yamanashi) links to source admin by country and name."""
    from shapely.geometry import box
    from winelib_utils.models import Appellation, Base, Region
    url = f"sqlite:///{tmp_path / 'wine.db'}"
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    it, jp = Region(name="Italy", country="Italy"), Region(name="Japan", country="Japan")
    s.add_all([Appellation(name="Toscana", region_obj=it), Appellation(name="Yamanashi-ken", region_obj=jp),
               Appellation(name="Nagano-ken", region_obj=jp)])
    s.commit()
    s.close()
    geo = tmp_path / "geo"
    link.build_shapes.write(str(geo / "shapes"), "admin", [("Italy:Toscana", "Toscana", None, box(10, 43, 12, 44).wkb),
                                                            ("Japan:Yamanashi-ken", "Yamanashi-ken", None, box(138, 35, 139, 36).wkb)],
                            "appellation")
    link.main(str(geo), url, commit=True)
    assert boundaries(engine, "appellations") == {"Toscana": "admin:Italy:Toscana", "Yamanashi-ken": "admin:Japan:Yamanashi-ken",
                                                  "Nagano-ken": None}


def test_one_country_source_by_name_and_alias(tmp_path, link):
    """INAO's areas (France): names with accents and hyphens aside, the "X ou Y" forms, and the Vin de Pays aliases."""
    from shapely.geometry import box
    from winelib_utils.models import Appellation, Base, Region
    url = f"sqlite:///{tmp_path / 'wine.db'}"
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    fr, it = Region(name="Bourgogne", country="France"), Region(name="Italy", country="Italy")
    s.add_all([Appellation(name="Bourgogne Hautes-Côtes de Nuits", region_obj=fr),
               Appellation(name="Coteaux du Layon Faye d'Anjou", region_obj=fr),
               Appellation(name="Vin de Pays du Vaucluse", region_obj=fr),
               Appellation(name="Macon-Verzé", region_obj=it)])  # not France: not linked
    s.commit()
    s.close()
    geo = tmp_path / "geo"
    b = box(4, 47, 5, 48).wkb
    link.build_shapes.write(str(geo / "shapes"), "inao_aires", [
        ("364", "Bourgogne Hautes Côtes de Nuits", None, b), ("2252", "Vaucluse", None, b),
        ("9", "Coteaux du Layon Faye d'Anjou ou Faye", None, b), ("1737", "Mâcon Verzé", None, b)], "appellation")
    link.main(str(geo), url, commit=True)
    assert boundaries(engine, "appellations") == {
        "Bourgogne Hautes-Côtes de Nuits": "inao_aires:364", "Coteaux du Layon Faye d'Anjou": "inao_aires:9",
        "Vin de Pays du Vaucluse": "inao_aires:2252", "Macon-Verzé": None}
