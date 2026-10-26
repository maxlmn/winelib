"""Market price (WineLabs.ai) and place coordinates (OpenStreetMap): the network is never used."""
import time

import pytest

import jobs
from db import Bottle, Place, Producer, Wine


def seed(s):
    p = Producer(name="Clos Rougeard")
    with_lwin = Wine(producer=p, cuvee="Le Bourg", vintage="2015", type="Red", lwin="1104321")
    without = Wine(producer=p, cuvee="Les Poyeux", vintage="2016", type="Red")
    s.add_all([Bottle(wine=with_lwin, qty=1, bottle_size="150cl", price=300, currency="EUR", location="H1"),
               Bottle(wine=without, qty=1, price=100, currency="EUR", location="H2"),
               Bottle(wine=with_lwin, qty=2, bottle_size="75cl", price=140, currency="EUR", location="H3"),
               Bottle(wine=with_lwin, qty=3, bottle_size="75cl", price=1000, currency="SGD", location="H4"),
               Bottle(wine=with_lwin, qty=0, bottle_size="75cl", price=140, currency="EUR", location="H5"),  # drunk
               Place(name="Odette", city="Singapore", country="Singapore"),
               Place(name="Le Chateaubriand", city="Paris", country="France", lat=48.87, lng=2.37),
               Place(name="@home", city="Singapore", country="Singapore")])


class Calls(list):
    answer: dict


@pytest.fixture
def winelabs(monkeypatch):
    from winelib_utils import update_market_prices as prices
    monkeypatch.setenv("WINELABS_API_KEY", "test-key")
    calls = Calls()
    calls.answer = {"price": 500.0, "currency": "EUR", "sales": 12}

    def fake(lwin, vintage, target_currency="GBP", log=print):
        calls.append((lwin, vintage, target_currency))
        return dict(calls.answer)
    monkeypatch.setattr(prices, "fetch_winelabs", fake)
    return calls


def test_market_price_saved_and_scaled_to_the_format(client, fetch_price, winelabs):
    r = fetch_price(1)
    assert r["found"] and r["last_price"] == 1000.0 and r["last_price_source"] == "WineLabs.ai"  # magnum: 2x
    assert client.get("/api/bottles/1").json()["last_price"] == 1000.0
    # every other bottle of the wine still in the cellar too: one call per currency
    assert r["others_updated"] == 2 and winelabs == [("1104321", "2015", "EUR"), ("1104321", "2015", "SGD")]
    assert client.get("/api/bottles/3").json()["last_price"] == 500.0
    assert client.get("/api/bottles/5").json()["last_price"] is None  # drunk


def test_implausible_price_from_few_sales_isnt_saved(client, fetch_price, winelabs):
    # Bottle 1 now holds 1000 EUR; one sale at 30x that is a mis-recorded sale
    winelabs.answer.update(price=15000.0, sales=1)
    r = fetch_price(1)
    assert r["found"] is False and "from 1 sale" in r["message"] and "not saved" in r["message"]
    assert client.get("/api/bottles/1").json()["last_price"] == 1000.0
    winelabs.answer.update(price=15000.0, sales=30)  # many sales: believed
    assert fetch_price(1)["last_price"] == 30000.0


def test_other_currency_converted_with_the_settings_rates(client, fetch_price, winelabs):
    settings = client.get("/api/settings").json()
    assert client.put("/api/settings", json={**settings, "exchange_rates": {"SGD": 1, "EUR": 1.5, "USD": 1.2}}).status_code == 200
    winelabs.answer.update(price=900.0, currency="USD", sales=10)
    r = fetch_price(1)
    assert r["found"] and round(r["last_price"], 2) == round(900 * 1.2 / 1.5 * 2, 2)  # USD -> EUR, magnum


def test_market_price_needs_an_lwin_and_a_key(client, monkeypatch):
    monkeypatch.setenv("WINELABS_API_KEY", "test-key")
    assert client.post("/api/bottles/2/market-price").status_code == 422
    monkeypatch.delenv("WINELABS_API_KEY")
    assert client.post("/api/bottles/1/market-price").status_code == 503
    assert client.post("/api/bottles/999/market-price").status_code == 404


HIT = [{"name": "Odette", "display_name": "Odette, 1 Saint Andrew's Road, Singapore", "lat": "1.2902", "lon": "103.8517",
        "category": "amenity", "type": "restaurant"},
       {"name": "Odette Street", "display_name": "Odette Street, Singapore", "lat": "1.3", "lon": "103.9",
        "category": "highway", "type": "residential"}]


@pytest.fixture
def osm(monkeypatch):
    from winelib_utils import geocode
    queries = []
    monkeypatch.setattr(geocode, "_get_json", lambda url: queries.append(url) or HIT)
    return queries


def test_geocode_lookup(client, osm):
    hits = client.get("/api/lookups/geocode", params={"q": "Odette, Singapore"}).json()
    assert hits[0] == {"name": "Odette", "address": "Odette, 1 Saint Andrew's Road, Singapore", "lat": 1.2902,
                       "lng": 103.8517, "category": "amenity", "type": "restaurant"}
    assert "nominatim.openstreetmap.org" in osm[0]


def wait(client):
    for _ in range(200):
        job = client.get("/api/maintenance/job").json()
        if job and job["status"] != "running":
            return job
        time.sleep(0.02)
    raise AssertionError("job didn't finish")


def test_places_task_preview_then_save(client, osm):
    client.post("/api/maintenance/places", json={})
    job = wait(client)
    assert job["result"]["summary"] == "1 place without coordinates; 1 of 1 looked up found on OpenStreetMap."
    assert client.get("/api/places/1").json()["lat"] is None  # a preview saves nothing
    client.post("/api/maintenance/places", json={"commit": True})
    wait(client)
    jobs.current().thread.join(5)
    place = client.get("/api/places/1").json()
    assert (place["lat"], place["lng"]) == (1.2902, 103.8517)  # the restaurant, not the street
