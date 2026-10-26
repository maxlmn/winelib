"""Settings › Maintenance › Market prices: every cellar bottle with an LWIN, one WineLabs call per wine and vintage."""
import time
from datetime import date

import jobs
from db import Bottle, Producer, Wine


def seed(s):
    p = Producer(name="Domaine Roulot")
    wines = [Wine(producer=p, cuvee="Vireuils", vintage="2023", type="White", lwin="1080098"),
             Wine(producer=p, cuvee="Luchets", vintage="2022", type="White", lwin="1080099"),
             Wine(producer=p, cuvee="Tessons", vintage="2021", type="White")]  # no LWIN
    s.add_all(wines)
    s.flush()
    s.add_all([Bottle(wine_id=1, qty=1, location="H1", price=195, currency="EUR", last_price=89.99),
               Bottle(wine_id=1, qty=2, location="H2", price=180, currency="EUR"),
               Bottle(wine_id=1, qty=1, location="H3", price=190, currency="EUR", last_price=250,
                      last_price_date=date.today()),  # priced recently: skipped
               Bottle(wine_id=2, qty=0, location="H1", price=150, currency="EUR"),  # drunk
               Bottle(wine_id=3, qty=1, location="H1", price=120, currency="EUR")])


def wait(client):
    for _ in range(200):
        job = client.get("/api/maintenance/job").json()
        if job and job["status"] != "running":
            return job
        time.sleep(0.02)
    raise AssertionError("job didn't finish")


def test_preview_then_run(client, monkeypatch):
    from tasks import update_market_prices as prices
    calls = []
    monkeypatch.setattr(prices, "api_key", lambda: "k")
    monkeypatch.setattr(prices, "fetch_winelabs",
                        lambda lwin, vintage, target_currency="GBP", log=print: calls.append(lwin) or
                        {"price": 250.59, "currency": "EUR", "sales": 7})
    monkeypatch.setattr(prices, "time", type("T", (), {"sleep": staticmethod(lambda s: None)}))

    client.post("/api/maintenance/prices", json={})
    job = wait(client)
    assert job["result"]["summary"].startswith(
        "2 cellar bottles with an LWIN not priced in 90 days: 0 from your Bordeaux Index portfolio; for the rest (1 wine) "
        "a run asks the BI market then WineLabs.ai")
    assert not calls
    client.post("/api/maintenance/prices", json={"commit": True})
    job = wait(client)
    jobs.current().thread.join(5)
    assert calls == ["1080098"], job["log"]
    assert job["result"]["summary"] == "2 of 2 bottles priced; 2 changed or without a price."
    assert {i["detail"] for i in job["result"]["items"]} == {"90 EUR → 251 EUR", "– → 251 EUR"}


def test_force_refresh_previews_every_bottle(client, monkeypatch):
    from tasks import update_market_prices as prices
    monkeypatch.setattr(prices, "api_key", lambda: "k")
    client.post("/api/maintenance/prices_force", json={})
    job = wait(client)
    assert job["result"]["summary"].startswith("3 cellar bottles with an LWIN: 0 from your Bordeaux Index portfolio")
    assert len(job["result"]["items"]) == 3  # the one priced today too


def test_prices_younger_than_90_days_are_kept(client):
    from datetime import timedelta

    from tasks import update_market_prices as prices
    from db import get_session
    from main import app
    session = next(app.dependency_overrides[get_session]())
    b = session.get(Bottle, 3)
    for days, due in ((0, False), (89, False), (90, False), (91, True), (400, True)):
        b.last_price_date = date.today() - timedelta(days=days)
        session.commit()
        assert (3 in {x.id for x in prices.cellar_bottles(session)}) is due, days
    b.last_price_date = date.today()
    session.commit()
    session.close()


def test_market_price_button_previews_every_sibling(client, fetch_price, monkeypatch):
    """The button proposes a price for every bottle of the wine in the cellar, however recent; nothing is saved
    until it's confirmed."""
    from tasks import bordeaux_index as bi
    from tasks import update_market_prices as prices
    from db import get_session
    from main import app
    monkeypatch.setattr(prices, "api_key", lambda: "k")
    monkeypatch.setattr(bi, "configured", lambda: False)
    monkeypatch.setattr(prices, "fetch_winelabs", lambda lwin, vintage, target_currency="GBP", log=print:
                        {"price": 300.0, "currency": "EUR", "sales": 9})
    from datetime import timedelta
    session = next(app.dependency_overrides[get_session]())
    session.get(Bottle, 2).last_price_date = date.today() - timedelta(days=120)  # due again
    session.get(Bottle, 3).last_price_date = date.today() - timedelta(days=10)  # recent
    session.get(Bottle, 3).last_price = 250
    session.commit()
    session.close()

    preview = client.post("/api/bottles/1/market-price").json()
    proposed = {p["bottle_id"]: (p["old"], p["new"]) for p in preview["prices"]}
    assert proposed[3] == (250, 300.0) and proposed[1][1] == 300.0
    session = next(app.dependency_overrides[get_session]())
    assert session.get(Bottle, 3).last_price == 250 and session.get(Bottle, 1).last_price != 300  # not saved yet
    session.close()

    r = fetch_price(1)
    assert r["last_price"] == 300.0
    session = next(app.dependency_overrides[get_session]())
    assert session.get(Bottle, 3).last_price == 300  # priced 10 days ago: refreshed too
    assert session.get(Bottle, 2).last_price == 300
    session.close()


def test_bordeaux_index_first_then_winelabs(client, monkeypatch):
    """A wine in the BI portfolio takes BI's price (last trade per bottle, GBP -> the bottle's currency); WineLabs
    is only asked for the others."""
    from tasks import bordeaux_index as bi
    from tasks import update_market_prices as prices
    from db import get_session
    from main import app
    winelabs = []
    monkeypatch.setattr(prices, "api_key", lambda: "k")
    monkeypatch.setattr(prices, "fetch_winelabs", lambda lwin, vintage, target_currency="GBP", log=print:
                        winelabs.append(lwin) or {"price": 100.0, "currency": "EUR", "sales": 9})
    monkeypatch.setattr(prices, "time", type("T", (), {"sleep": staticmethod(lambda s: None)}))
    monkeypatch.setattr(bi, "configured", lambda: True)
    # Vireuils 2023 in 6 x 75cl, last traded at 1,200 GBP the case: 200 GBP a bottle
    monkeypatch.setattr(bi, "portfolio", lambda: [
        {"portfolioRef": "ST_1", "lwin18": 108009820230600750, "packSize": 6, "vintageYear": 2023, "quantity": 1,
         "size": 75, "bids": [{"price": 1100}], "lastTrade": {"price": 1200}}])
    monkeypatch.setattr(prices, "exchange_rates", lambda session=None: {"SGD": 1.0, "EUR": 1.5, "GBP": 1.8})
    monkeypatch.setattr(bi, "market_quote", lambda *key: None)

    session = next(app.dependency_overrides[get_session]())
    vireuils = prices.cellar_bottles(session, max_age_days=0)
    done = prices.refresh_prices(session, vireuils)
    by_source = {(b.wine.cuvee, b.last_price_source) for b, _, p in done if p}
    assert by_source == {("Vireuils", "Bordeaux Index")}
    assert {round(p, 2) for _, _, p in done if p} == {240.0}  # 200 GBP * 1.8 / 1.5 = 240 EUR
    assert winelabs == []  # every bottle here is in the BI portfolio
    session.close()


def test_market_price_button_falls_back_to_winelabs(client, fetch_price, monkeypatch):
    from tasks import bordeaux_index as bi
    from tasks import update_market_prices as prices
    monkeypatch.setattr(prices, "api_key", lambda: "k")
    monkeypatch.setattr(bi, "configured", lambda: True)
    monkeypatch.setattr(bi, "portfolio", lambda: [])  # BI doesn't hold it
    monkeypatch.setattr(bi, "market_quote", lambda *key: None)  # nor quote it
    bi.forget_portfolio()  # an earlier test's copy holds this wine
    monkeypatch.setattr(prices, "fetch_winelabs", lambda lwin, vintage, target_currency="GBP", log=print:
                        {"price": 260.0, "currency": "EUR", "sales": 9})
    r = fetch_price(2)
    assert r["found"] and r["last_price_source"] == "WineLabs.ai" and r["last_price"] == 260.0


def test_bi_market_prices_wines_not_in_the_portfolio(client, monkeypatch):
    """Not in the portfolio: GET /v2/market/lwin18/{LWIN7 + vintage + pack + ml}, trying 6 then 12 bottles."""
    from tasks import bordeaux_index as bi
    from tasks import update_market_prices as prices
    from db import get_session
    from main import app
    asked = []

    def request(method, path, body=None, token=None, timeout=30):
        asked.append(path)
        if path.endswith("108009820231200750"):  # Vireuils 2023, 12 x 75cl
            return {"lwinProductName": "Roulot, Meursault Vireuils", "bids": [{"price": 2300}], "offers": [{"price": 3000}],
                    "lastTrade": {"price": 2400}}
        if path.endswith("108009820230600750"):  # in 6 x 75cl: bids, never traded
            return {"lwinProductName": "Roulot, Meursault Vireuils", "bids": [{"price": 1300}]}
        raise bi.BIError("404 Not found")
    monkeypatch.setattr(bi, "configured", lambda: True)
    monkeypatch.setattr(bi, "token", lambda: "t")
    monkeypatch.setattr(bi, "_request", request)
    monkeypatch.setattr(bi, "portfolio", lambda: [])
    monkeypatch.setattr(prices, "api_key", lambda: None)  # no WineLabs: BI alone
    monkeypatch.setattr(prices, "exchange_rates", lambda session=None: {"SGD": 1.0, "EUR": 1.5, "GBP": 1.8})

    session = next(app.dependency_overrides[get_session]())
    b = session.get(Bottle, 1)
    assert round(prices.price_bottle(b, {}, log=lambda line: None, bi={}, market={}), 2) == 240.0  # 2400/12 GBP -> EUR
    assert b.last_price_source == "Bordeaux Index"
    assert asked == ["/v2/market/lwin18/108009820230600750", "/v2/market/lwin18/108009820231200750"]
    session.rollback()
    session.close()


def test_lwin18():
    from tasks.bordeaux_index import lwin18
    assert lwin18("1080098", "2023", 6, 75) == "108009820230600750"
    assert lwin18("1000013", "NV - Oct 2024", 6, 150) == "100001310000601500"
    assert lwin18("108009", "2023", 6, 75) is None and lwin18("1080098", "2023", 6, None) is None
