"""Migration 0017: the stray "Roussette" grape (VIVC 10264) merged into Altesse, its wines moved."""
import importlib.util
import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import db
from db import Producer, Varietal, Wine, WineGrape

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    "m0017", os.path.join(HERE, "migrations", "versions", "0017_roussette_is_altesse.py"))
m0017 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m0017)


def engine_with(tmp_path, altesse=True):
    engine = create_engine(f"sqlite:///{tmp_path / 'm.db'}")
    db.Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as s:
        rous = Varietal(name="Roussette", vivc=10264, color="White", climate="Cool", classic_regions="France: Savoie")
        jac = Varietal(name="Jacquère")
        s.add_all([rous, jac])
        if altesse:
            alt = Varietal(name="Altesse", vivc=354, color="White")
            s.add(alt)
        p = Producer(name="Berlioz")
        w1 = Wine(producer=p, cuvee="Zulime", vintage="2022", varietal=rous)
        w1.grapes = [WineGrape(varietal=rous)]
        w2 = Wine(producer=p, cuvee="Both", vintage="2021", varietal=rous)
        w2.grapes = [WineGrape(varietal=rous), WineGrape(varietal=jac)] + ([WineGrape(varietal=alt)] if altesse else [])
        s.add_all([w1, w2])
        s.commit()
    return engine


def test_merged_into_altesse(tmp_path):
    engine = engine_with(tmp_path)
    with engine.begin() as conn:
        m0017.merge(conn)
    with sessionmaker(bind=engine)() as s:
        assert s.query(Varietal).filter_by(name="Roussette").first() is None
        alt = s.query(Varietal).filter_by(name="Altesse").one()
        assert alt.aliases == "Roussette, Roussette de Savoie" and alt.climate == "Cool" and alt.classic_regions == "France: Savoie"
        for w in s.query(Wine).all():
            assert w.varietal_id == alt.id
            ids = [g.varietal_id for g in w.grapes]
            assert ids.count(alt.id) == 1 and len(ids) == len(set(ids))  # never a grape twice
    with engine.begin() as conn:  # run again: nothing to do
        m0017.merge(conn)
        assert conn.execute(text("SELECT count(*) FROM varietals WHERE name = 'Altesse'")).scalar() == 1


def test_renamed_without_altesse(tmp_path):
    engine = engine_with(tmp_path, altesse=False)
    with engine.begin() as conn:
        m0017.merge(conn)
    with sessionmaker(bind=engine)() as s:
        alt = s.query(Varietal).filter_by(name="Altesse").one()
        assert alt.vivc == 354 and "Roussette" in alt.aliases and len(alt.wines) == 2
