"""Bordeaux Index view: BI portfolio lines per bottle in GBP, next to the app's bottles. No network."""
import pytest

from db import Bottle, Producer, Wine

PORTFOLIO = [
    {"portfolioRef": "ST_1_1", "lwin18": 101234520190600750, "productName": "Domaine Jamet, Cote Rotie", "packSize": 6,
     "vintageYear": 2019, "quantity": 2, "location": "UKWAREHOUSE", "costPrice": 600, "producer": "Domaine Jamet",
     "size": 75, "dutyStatus": "IB", "bids": [{"price": 660}, {"price": 640}], "offers": [{"price": 780}],
     "lastTrade": {"price": 720, "date": "2026-09-01"}},
    {"portfolioRef": "ST_1_2", "lwin18": 109999920150600750, "productName": "Unknown Wine", "packSize": 6,
     "vintageYear": 2015, "quantity": 1, "costPrice": 300, "size": 75, "bids": [{"price": 240}], "offers": [],
     "lastTrade": None},
]


def seed(s):
    p = Producer(name="Domaine Jamet")
    w = Wine(producer=p, cuvee="", vintage="2019", type="Red", lwin="1012345")
    s.add(w)
    s.flush()
    other = Wine(producer=p, cuvee="Cornas", vintage="2018", type="Red", lwin="1055555")
    s.add(other)
    s.flush()
    s.add_all([Bottle(wine_id=w.id, qty=10, location="Bonded", price=100, currency="GBP", last_price=120, bottle_size="750ml"),
               Bottle(wine_id=w.id, qty=1, location="H1", price=100, currency="GBP", bottle_size="150cl"),
               Bottle(wine_id=w.id, qty=3, location="H2", price=100, currency="GBP", bottle_size="75cl"),  # at home: not BI's
               Bottle(wine_id=other.id, qty=2, location="Bonded 2", price=50, currency="GBP")])  # at Bonded, not at BI


@pytest.fixture
def bi(monkeypatch):
    from winelib_utils import bordeaux_index as bi
    for k in ("BI_EMAIL", "BI_PASSWORD", "BI_SALES_LEDGER", "BI_PURCHASE_LEDGER"):
        monkeypatch.setenv(k, "x")
    monkeypatch.setattr(bi, "portfolio", lambda: PORTFOLIO)
    bi.forget_portfolio()
    return bi


def test_lines_per_bottle_in_gbp(client, bi):
    r = client.get("/api/bordeaux-index").json()
    assert r["available"] and r["error"] is None
    jamet = r["lines"][0]
    assert (jamet["bottles"], jamet["cost"], jamet["bid"], jamet["offer"], jamet["last"]) == (12, 100, 110, 130, 120)
    assert jamet["value"] == 1440  # 12 bottles at the last trade
    # Only bottles held at Bonded (not the 3 at home, not the magnum); "750ml" matches BI's 75cl
    assert jamet["app"]["bottles"] == 10 and jamet["app"]["locations"] == ["Bonded"]
    assert jamet["app"]["color"] == "Red"  # with its region: the line's bottle end
    assert r["location"] == "Bonded"
    assert r["lines"][1]["value"] == 240 and r["lines"][1]["app"]["bottles"] == 0  # no trade yet: the best bid
    t = r["totals"]
    assert (t["bottles"], t["cost"], t["value"], t["unmatched"]) == (18, 1500, 1680, 1)
    assert t["app_value"] == 1200 and t["app_bottles"] == 12 and t["app_only"] == 2
    # At Bonded in the app, but not in the BI portfolio
    assert [(b["cuvee"], b["qty"], b["location"]) for b in r["app_only"]] == [("Cornas", 2, "Bonded 2")]
    assert r["app_only"][0]["color"] == "Red"


def test_bi_location_comes_from_settings(client, bi):
    import settings
    from conftest import TEST_SETTINGS
    try:
        settings.apply(TEST_SETTINGS.model_copy(update={"bi_location": "H2"}))
        jamet = client.get("/api/bordeaux-index").json()["lines"][0]
        assert jamet["app"]["bottles"] == 3 and jamet["app"]["locations"] == ["H2"]
    finally:
        settings.apply(TEST_SETTINGS)


def test_sizes_compare_in_cl():
    from winelib_utils.bordeaux_index import size_cl
    assert size_cl("75cl") == size_cl("750ml") == size_cl("0.75l") == size_cl(75) == size_cl(None) == 75
    assert size_cl("37.5cl") == 37.5 and size_cl("Magnum") == 150 and size_cl("Barrel") is None


def test_not_configured(client, monkeypatch):
    for k in ("BI_EMAIL", "BI_PASSWORD", "BI_SALES_LEDGER", "BI_PURCHASE_LEDGER"):
        monkeypatch.delenv(k, raising=False)
    assert client.get("/api/bordeaux-index").json()["available"] is False


def test_api_error_is_reported(client, bi, monkeypatch):
    def fail():
        raise bi.BIError("Bordeaux Index refused the login (401 Invalid credentials)")
    monkeypatch.setattr(bi, "portfolio", fail)
    r = client.get("/api/bordeaux-index?refresh=true").json()
    assert "refused the login" in r["error"] and r["lines"] == []


def test_split_lwin18():
    from winelib_utils.bordeaux_index import split_lwin18
    assert split_lwin18(100006920071200750) == ("1000069", "2007", 12, 750)
    assert split_lwin18("123") == (None, None, None, None)


def test_no_trade_nor_bid_is_valued_at_cost(client, bi, monkeypatch):
    from winelib_utils import update_market_prices as prices
    bare = {**PORTFOLIO[1], "portfolioRef": "ST_1_3", "bids": [], "lastTrade": None}
    monkeypatch.setattr(bi, "portfolio", lambda: [PORTFOLIO[0], bare])
    bi.forget_portfolio()
    r = client.get("/api/bordeaux-index").json()
    by_ref = {l["ref"]: l for l in r["lines"]}
    assert by_ref["ST_1_1"]["basis"] == "last" and by_ref["ST_1_3"]["basis"] == "cost"
    assert by_ref["ST_1_3"]["value"] == 300  # 6 bottles at the 50 cost
    assert r["totals"]["value"] == 1740 and r["totals"]["value_matched"] == 1440  # only Jamet is in the app
    assert prices.bi_quotes(refresh=True) == {("1012345", "2019", 75.0): 120}  # cost never prices the app's bottles


def test_bi_values_become_the_apps_market_prices(client, bi, monkeypatch):
    from winelib_utils import update_market_prices as prices
    monkeypatch.setattr(prices, "exchange_rates", lambda session=None: {"SGD": 1.0, "GBP": 1.7, "EUR": 1.5})
    bi.forget_portfolio()
    preview = client.post("/api/bordeaux-index/apply-values", json={}).json()
    (change,) = preview["changes"]  # the 10 Jamet at Bonded; Unknown Wine isn't in the app
    assert (change["bottle_id"], change["old"], change["new"], change["basis"]) == (1, 120, 120, "last")
    assert preview["saved"] == 0
    assert client.post("/api/bordeaux-index/apply-values", json={"commit": True}).json()["saved"] == 1
    b = client.get("/api/bottles/1").json()
    assert b["last_price_source"] == "Bordeaux Index" and b["last_price"] == 120


def test_a_bid_alone_never_prices_a_bottle(bi):
    """Only a last trade is a price: a line with bids and no trade gives no quote (WineLabs then)."""
    bid_only = {**PORTFOLIO[0], "lastTrade": None}
    assert bi.quotes([bi.line(bid_only)]) == {}
