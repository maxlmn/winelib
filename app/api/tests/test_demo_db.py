"""scripts/make_demo_db.py: a demo database cut from yours (the most represented producers, their wines, bottles,
tastings and places), without prices, review texts or private notes."""
import importlib.util
import os
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import migrate
from db import (Appellation, Bottle, CriticScore, Place, Producer, Region, RestaurantVisit, TastingNote, Vineyard,
                Wine)

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "..", "..", "scripts", "make_demo_db.py")


def load_script():
    spec = importlib.util.spec_from_file_location("make_demo_db", SCRIPT)
    demo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(demo)
    return demo


def yours(engine):
    with Session(engine) as s:
        loire = Region(id=3, name="Loire")
        sc = Appellation(id=10, name="Saumur-Champigny", region_obj=loire)
        mine_only = Vineyard(id=99, name="Weinlage of mine")
        bistro = Place(name="Le Bistrot", city="Saumur", notes="ask for Paul")
        rougeard = Producer(name="Clos Rougeard", region_obj=loire, notes="private")
        bourg = Wine(producer=rougeard, cuvee="Le Bourg", vintage="2016", appellation=sc, vineyard=mine_only)
        bourg.scores.append(CriticScore(critic="Robert Parker", score="96", note="Their text.", url="https://rp/1"))
        bottle = Bottle(wine=bourg, qty=3, location="H1", price=400, currency="EUR", vendor="Caviste")
        s.add_all([bottle, TastingNote(bottle=bottle, date=date(2025, 5, 1), rating=95, notes="Superb.", place=bistro),
                   RestaurantVisit(place=bistro, date=date(2025, 5, 1), notes="Dinner"),
                   Wine(producer=Producer(name="Rarely drunk"), cuvee="X", vintage="2020")])
        s.add(Bottle(wine=s.query(Wine).filter_by(cuvee="X").one(), qty=1, location="H2"))
        s.commit()


def test_a_cut_of_your_database(tmp_path):
    demo = load_script()
    src, dst = create_engine(f"sqlite:///{tmp_path / 'yours.db'}"), create_engine(f"sqlite:///{tmp_path / 'demo.db'}")
    migrate.upgrade(src)
    migrate.upgrade(dst)
    yours(src)
    with Session(dst) as d:  # the reference data the demo starts from (same ids as yours)
        d.add_all([Region(id=3, name="Loire"), Appellation(id=10, name="Saumur-Champigny", region_id=3)])
        d.commit()
    with Session(src) as s, Session(dst) as d:
        assert demo.copy(s, d, n=1) == {"producers": 1, "wines": 1, "scores": 1, "bottles": 1, "tastings": 1,
                                        "places": 1, "visits": 1}
        (p,) = d.query(Producer).all()
        assert (p.name, p.notes, p.region_id) == ("Clos Rougeard", None, 3)  # the most represented only
        (w,) = d.query(Wine).all()
        assert (w.appellation_id, w.vineyard_id) == (10, None)  # your own vineyard doesn't ship
        (sc,) = w.scores
        assert (sc.critic, sc.score, sc.note, sc.url) == ("Robert Parker", "96", None, "https://rp/1")  # no text
        (b,) = d.query(Bottle).all()
        assert (b.qty, b.location, b.price, b.vendor) == (3, "H1", None, None)
        (t,) = d.query(TastingNote).all()
        assert (t.rating, t.notes, t.place.name, t.place.notes) == (95, "Superb.", "Le Bistrot", None)
        assert d.query(RestaurantVisit).one().notes == "Dinner"
