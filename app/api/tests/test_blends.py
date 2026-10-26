"""A wine's grapes (wine_grapes, the first the main one, kept equal to wines.varietal_id) and its blend style."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from db import Base, Producer, Varietal, Wine
from tasks.blends import blend_style


def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'b.db'}")
    Base.metadata.create_all(engine)
    return Session(engine)


def names(w):
    return [(g.varietal.name, g.share) for g in w.grapes]


def test_the_main_grape_and_the_list_stay_one(tmp_path):
    s = session(tmp_path)
    cs, merlot, cf, syrah = (Varietal(name=n) for n in ("Cabernet Sauvignon", "Merlot", "Cabernet Franc", "Syrah"))
    p = Producer(name="Château X")
    s.add_all([cs, merlot, cf, syrah, p])
    s.flush()
    # code that only sets the main grape (an import): it becomes the first grape
    w = Wine(producer=p, cuvee="", vintage="2019", varietal=cs)
    s.add(w)
    s.flush()
    assert names(w) == [("Cabernet Sauvignon", None)]
    # a list: the first is the main grape
    w.set_grapes([(merlot, 60), (cs, 30), (cf, 10)])
    s.flush()
    assert names(w) == [("Merlot", 60), ("Cabernet Sauvignon", 30), ("Cabernet Franc", 10)] and w.varietal is merlot
    # the main grape changed alone: it replaces the first, the others stay
    w.varietal = syrah
    s.flush()
    assert names(w) == [("Syrah", None), ("Cabernet Sauvignon", 30), ("Cabernet Franc", 10)]
    # to one already in the list: it moves first
    w.varietal = cf
    s.flush()
    assert names(w) == [("Cabernet Franc", 10), ("Cabernet Sauvignon", 30)]
    assert [g.position for g in w.grapes] == [1, 2]
    # by id only (an import: wine.varietal_id = grape.id)
    w.varietal_id = syrah.id
    s.flush()
    s.expire(w)
    assert names(w)[0] == ("Syrah", None) and w.varietal_id == syrah.id
    # none
    w.set_grapes([])
    s.flush()
    assert w.grapes == [] and w.varietal_id is None


def test_blend_styles_from_old_texts():
    assert [blend_style(t) for t in ("Bordeaux Blend", "Bordeau Blend", "Rhone Blend", "Southern Blend", "GSM",
                                     "Champagne Blend", "Local Blend", "Rioja Blend", "Blend", "", None,
                                     "Rhône blend", "Field Blend", "Gemischter Satz")] == [
        "Bordeaux blend", "Bordeaux blend", "Rhône blend", "Rhône blend", "Rhône blend", "Champagne blend",
        "Other blend", "Other blend", "Other blend", None, None, "Rhône blend", "Field blend", "Field blend"]
