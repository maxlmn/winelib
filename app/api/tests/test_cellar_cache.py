"""The cellar is read once per request (a page and its maps' figures share it), again after a write."""
from db import Bottle, Producer, Wine


def seed(s):
    s.add(Bottle(wine=Wine(producer=Producer(name="Clos Rougeard"), cuvee="Le Bourg", vintage="2016"), qty=2,
                 location="H1"))


def test_cellar_read_once_per_session_until_written(client):
    from cellar import load_cellar
    from db import get_session
    from main import app
    s = next(app.dependency_overrides[get_session]())
    first = load_cellar(s)
    assert load_cellar(s) is first
    s.query(Bottle).first().qty += 1
    s.flush()
    again = load_cellar(s)
    assert again is not first and [b["qty"] for b in again[0]] == [3]
    s.rollback()
    s.close()
