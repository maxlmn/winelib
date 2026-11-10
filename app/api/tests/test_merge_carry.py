"""What a merged wine keeps (carry() in app/api/tasks/merge_cuvees.py, behind Duplicate wines, Merge cuvées and Merge
producers): its duplicate's grapes and shares, its empty fields, its list entries once; which wines are duplicates;
merging only the groups ticked in the preview."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import db
from db import Bottle, ListItem, Producer, Region, Varietal, Vineyard, Wine, WineList
from conftest import wait_job as wait


def seed(s):
    # two groups of duplicates for the Duplicate wines task: picking one merges only that one
    p, q = Producer(name="Domaine Un"), Producer(name="Domaine Deux")
    s.add_all([Wine(producer=p, cuvee="A", vintage="2015", type="Red"),
               Wine(producer=p, cuvee="A", vintage="2015", type="Red"),
               Wine(producer=q, cuvee="B", vintage="2016", type="White"),
               Wine(producer=q, cuvee="B", vintage="2016", type="White")])


@pytest.fixture
def s(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'w.db'}")
    db.sqlite_pragmas(engine)
    db.Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def grapes(w):
    return [(g.varietal.name, g.share) for g in w.grapes]


def two(s, kept_grapes, dup_grapes, **dup):
    """A wine entered twice: the first (kept) with those grapes, the second with its own and the fields given."""
    p = Producer(name="P")
    v = {n: Varietal(name=n) for n in ("Cab", "Merlot", "Franc")}
    a = Wine(producer=p, cuvee="X", vintage="2015", type="Red")
    b = Wine(producer=p, cuvee="X", vintage="2015", type="Red", **dup)
    a.set_grapes([(v[n], sh) for n, sh in kept_grapes])
    b.set_grapes([(v[n], sh) for n, sh in dup_grapes])
    s.add_all([a, b])
    s.commit()
    return a, b


def merge_all(s):
    from tasks import consolidate_duplicate_wines as dup
    groups = dup.find_duplicate_groups(s)
    dup.merge_groups(s, groups, log=lambda _: None)
    s.expire_all()
    return groups


def test_duplicates_blend_is_kept(s):
    a, b = two(s, [("Cab", None)], [("Cab", 70), ("Merlot", 30)])
    merge_all(s)
    assert s.get(Wine, b.id) is None
    assert grapes(s.get(Wine, a.id)) == [("Cab", 70), ("Merlot", 30)]


def test_kept_blend_wins_and_no_grape_is_lost(s):
    a, b = two(s, [("Cab", 60), ("Merlot", 40)], [("Cab", None), ("Franc", None)])
    merge_all(s)
    w = s.get(Wine, a.id)
    assert grapes(w) == [("Cab", 60), ("Merlot", 40), ("Franc", None)]  # Franc only the duplicate had
    assert w.varietal.name == "Cab"


def test_shares_never_add_up_past_100(s):
    a, b = two(s, [("Cab", 80), ("Merlot", 20)], [("Cab", 70), ("Franc", 30)])  # as complete: the kept one's
    merge_all(s)
    assert grapes(s.get(Wine, a.id)) == [("Cab", 80), ("Merlot", 20), ("Franc", None)]


def test_empty_fields_filled_from_the_duplicate(s):
    from tasks.merge_cuvees import carry
    r = Region(name="Loire")
    vy = Vineyard(name="Clos")
    p = Producer(name="P")
    a = Wine(producer=p, cuvee="X", vintage="2015", type="Red")
    b = Wine(producer=p, cuvee="X", vintage="2015", type="Red", region_obj=r, vineyard=vy, lwin="1234567",
             blend="Field blend", drink_window_start=2020)
    s.add_all([a, b])
    s.commit()
    carry(a, b)
    assert (a.region_id, a.vineyard_id, a.lwin, a.blend, a.drink_window_start) == (r.id, vy.id, "1234567",
                                                                                     "Field blend", 2020)
    keep = Wine(producer=p, cuvee="X", vintage="2016", type="Red", lwin="7654321")
    s.add(keep)
    s.flush()
    carry(keep, b)
    assert keep.lwin == "7654321"  # its own kept


def test_different_regions_vineyards_or_lwin_are_not_duplicates(s):
    from tasks import consolidate_duplicate_wines as dup
    p = Producer(name="P")
    ra, rb = Region(name="A"), Region(name="B")
    s.add_all([Wine(producer=p, cuvee="", vintage="2018", type="White", region_obj=ra),
               Wine(producer=p, cuvee=None, vintage="2018", type="White", region_obj=rb),
               Wine(producer=p, cuvee="Y", vintage="2018", type="White", lwin="1111111"),
               Wine(producer=p, cuvee="Y", vintage="2018", type="White"),  # one LWIN, one none
               Wine(producer=p, cuvee="Z", vintage="2018", type="White", vineyard=Vineyard(name="V")),
               Wine(producer=p, cuvee="Z", vintage="2018", type="White"),
               Wine(producer=p, cuvee="W", vintage="2018", type="White", region_obj=ra),
               Wine(producer=p, cuvee="W ", vintage="2018", type="White", region_obj=ra)])  # the same
    s.commit()
    (group,) = dup.find_duplicate_groups(s)
    assert {s.get(Wine, i).cuvee for i in [group["primary"], *group["duplicates"]]} == {"W", "W "}


def test_twin_found_whether_no_name_is_null_or_empty(s):
    from tasks.merge_producers import merge_producer
    k, d = Producer(name="Keep"), Producer(name="Drop")
    a = Wine(producer=k, cuvee="", vintage="2015", type="Red", disgorgement_date=None)
    b = Wine(producer=d, cuvee=None, vintage="2015", type="Red", disgorgement_date="")
    s.add_all([a, b])
    s.flush()
    s.add(Bottle(wine=b, qty=2))
    s.commit()
    r = merge_producer(s, k.id, d.id, log=lambda _: None)
    s.commit()
    assert r["merged"] == 1 and s.query(Wine).count() == 1
    assert s.query(Bottle).one().wine_id == a.id


def test_a_list_holding_both_keeps_one_entry(s):
    a, b = two(s, [], [])
    lst, other = WineList(name="L"), WineList(name="M")
    s.add_all([lst, other])
    s.flush()
    s.add_all([ListItem(list_id=lst.id, kind="wine", wine_id=a.id, producer_id=a.producer_id),
               ListItem(list_id=lst.id, kind="wine", wine_id=b.id, producer_id=b.producer_id, note="Gift"),
               ListItem(list_id=other.id, kind="wine", wine_id=b.id, producer_id=b.producer_id)])
    s.commit()
    merge_all(s)
    assert sorted((i.list_id, i.wine_id, i.note) for i in s.query(ListItem)) == [(lst.id, a.id, "Gift"),
                                                                                 (other.id, a.id, None)]


def test_a_list_holding_both_producers_keeps_one_entry(s):
    from tasks.merge_producers import merge_producer
    k, d = Producer(name="Keep"), Producer(name="Drop")
    lst = WineList(name="L")
    s.add_all([k, d, lst])
    s.flush()
    s.add_all([ListItem(list=lst, kind="producer", producer_id=k.id, note="Visit"),
               ListItem(list=lst, kind="producer", producer_id=d.id, note="Ask for the 2010")])
    s.commit()
    merge_producer(s, k.id, d.id, log=lambda _: None)
    s.commit()
    assert [(i.producer_id, i.note) for i in s.query(ListItem)] == [(k.id, "Visit\n\nAsk for the 2010")]


def test_duplicates_merges_only_the_ticked_groups(client):
    client.post("/api/maintenance/duplicates", json={})
    items = wait(client)["result"]["items"]
    assert [(it["pick"]["key"], it["pick"]["group"], it["pick"]["on"]) for it in items] == [
        ("3:4", "Domaine Deux", True), ("1:2", "Domaine Un", True)]
    client.post("/api/maintenance/duplicates", json={"commit": True, "keys": ["3:4"]})
    job = wait(client)
    assert job["status"] == "done" and job["result"]["summary"] == "0 cellar lines moved into 1 wine, 1 duplicate deleted."
    assert client.get("/api/wines/4").status_code == 404 and client.get("/api/wines/2").status_code == 200
    client.post("/api/maintenance/duplicates", json={"commit": True, "keys": ["1:9"]})  # no longer that group
    assert wait(client)["result"]["summary"].startswith("0 cellar lines moved into 0 wines")
    client.post("/api/maintenance/duplicates", json={"commit": True})  # the Run button: every group
    wait(client)
    assert client.get("/api/wines/2").status_code == 404


def test_merge_cuvees_folds_into_the_twin_with_its_blend(s):
    from tasks.merge_cuvees import merge_cuvee
    p, cab, mer = Producer(name="P"), Varietal(name="Cab"), Varietal(name="Merlot")
    a = Wine(producer=p, cuvee="Les Poyeux", vintage="2016", type="Red", disgorgement_date=None)
    b = Wine(producer=p, cuvee="Poyeux", vintage="2016", type="Red", disgorgement_date="")  # '' is none
    a.set_grapes([(cab, None)])
    b.set_grapes([(cab, 70), (mer, 30)])
    s.add_all([a, b])
    s.commit()
    assert merge_cuvee(s, p.id, "Poyeux", "Les Poyeux", log=lambda _: None)["merged"] == 1
    s.commit()
    s.expire_all()
    assert s.get(Wine, b.id) is None and grapes(s.get(Wine, a.id)) == [("Cab", 70), ("Merlot", 30)]
