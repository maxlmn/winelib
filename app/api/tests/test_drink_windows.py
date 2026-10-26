"""Drinking windows: maturity in the cellar, drink-soon on the home page."""
from datetime import date

import pytest

from db import Bottle, Producer, Wine
from conftest import rp

Y = date.today().year


def seed(s):
    p = Producer(name="Domaine Jamet")
    s.add_all([
        Wine(producer=p, cuvee="Past", vintage="2005", type="Red", drink_window_start=Y - 15, drink_window_end=Y - 2),
        Wine(producer=p, cuvee="Closing", vintage="2012", type="Red", drink_window_start=Y - 5, drink_window_end=Y + 1),
        Wine(producer=p, cuvee="Ready", vintage="2016", type="Red", drink_window_start=Y - 2, drink_window_end=Y + 15),
        Wine(producer=p, cuvee="Young", vintage="2022", type="Red", drink_window_start=Y + 3, drink_window_end=Y + 25),
        Wine(producer=p, cuvee="Noted", vintage="2010", type="Red", scores=rp("94", note="Firm and deep. Drink 2020-2040.")),
        Wine(producer=p, cuvee="Paged", vintage="2019", type="Red", scores=rp("96", note="Dense.", url="https://www.robertparker.com/wines/abc/jamet")),
    ])
    s.flush()
    for wid in range(1, 5):
        s.add(Bottle(wine_id=wid, qty=wid, location=f"H{wid}", price=50, currency="SGD"))
    s.add(Bottle(wine_id=5, qty=1, location="H5", price=50, currency="SGD"))
    s.add(Bottle(wine_id=6, qty=1, location="H6", price=50, currency="SGD"))
    s.add(Wine(producer=p, cuvee="Drunk", vintage="2015", type="Red", scores=rp("95", note="Drink 2020-2030.")))  # no bottle


def test_maturity_in_the_cellar_and_on_the_wine_page(client):
    rows = {b["cuvee"]: b for b in client.get("/api/cellar").json()["bottles"]}
    assert {k: rows[k]["maturity"] for k in ("Past", "Closing", "Ready", "Young")} == {
        "Past": "past", "Closing": "ready", "Ready": "ready", "Young": "young"}
    assert client.get("/api/wines/4").json()["maturity"] == "young"
    assert client.get("/api/wines/5").json()["maturity"] is None


def test_home_lists_what_to_drink_soon(client):
    soon = client.get("/api/dashboard").json()["drink_soon"]
    assert [l["cuvee"] for l in soon["lines"]] == ["Past", "Closing", "Ready"]  # past first, then closing soonest
    assert soon["lines"][1]["years_left"] == 1
    assert soon["bottles"] == {"ready": 5, "young": 4, "past": 1, "unknown": 2}
