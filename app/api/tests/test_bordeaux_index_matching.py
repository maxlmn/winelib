"""Bordeaux Index reconciliation edge cases: BI's NV vintage (1000) and wines whose app LWIN isn't BI's."""
import pytest

from db import Appellation, Bottle, Producer, Wine

PORTFOLIO = [
    # Krug Grande Cuvée NV: BI writes the vintage as 1000
    {"portfolioRef": "ST_NV", "lwin18": 100001310000600750, "lwinProductName": "Krug, Grande Cuvee", "producer": "Krug",
     "packSize": 6, "vintageYear": 1000, "quantity": 1, "size": 75, "costPrice": 900, "bids": [{"price": 1020}],
     "lastTrade": {"price": 1080}},
    # BI's LWIN for Clos des Angles; the app filed it under Les Angles with another LWIN
    {"portfolioRef": "ST_ANG", "lwin18": 101111120190600750, "producer": "Domaine Marquis d'Angerville",
     "lwinProductName": "Domaine Marquis d'Angerville, Volnay Premier Cru, Clos des Angles", "packSize": 6,
     "vintageYear": 2019, "quantity": 1, "size": 75, "costPrice": 600, "lastTrade": {"price": 720}},
]


def seed(s):
    krug, angerville = Producer(name="Krug"), Producer(name="Marquis d'Angerville")
    volnay = Appellation(name="Volnay Premier Cru")
    gc = Wine(producer=krug, cuvee="Grande Cuvée", vintage="NV", disgorgement_date="Oct 2024", type="Bubbles", lwin="1000013")
    angles = Wine(producer=angerville, cuvee="Les Angles", vintage="2019", type="Red", appellation=volnay, lwin="1222222")
    champans = Wine(producer=angerville, cuvee="Champans", vintage="2019", type="Red", appellation=volnay, lwin="1333333")
    s.add_all([gc, angles, champans])
    s.flush()
    s.add_all([Bottle(wine_id=gc.id, qty=6, location="Bonded", price=150, currency="GBP"),
               Bottle(wine_id=angles.id, qty=6, location="Bonded", price=100, currency="GBP"),
               Bottle(wine_id=champans.id, qty=6, location="Bonded", price=100, currency="GBP")])


@pytest.fixture
def bi(monkeypatch):
    from winelib_utils import bordeaux_index as bi
    monkeypatch.setattr(bi, "configured", lambda: True)
    monkeypatch.setattr(bi, "portfolio", lambda: PORTFOLIO)
    bi.forget_portfolio()
    return bi


def lines(client):
    return {l["ref"]: l for l in client.get("/api/bordeaux-index").json()["lines"]}


def test_bi_nv_is_1000(client, bi):
    nv = lines(client)["ST_NV"]
    assert nv["vintage"] == "NV"
    assert (nv["app"]["bottles"], nv["app"]["match"]) == (6, "lwin")  # the app's "NV - Oct 2024" bottle


def test_clos_des_angles_matches_les_angles_by_name_then_takes_bis_lwin(client, bi):
    r = client.get("/api/bordeaux-index").json()
    ang = {l["ref"]: l for l in r["lines"]}["ST_ANG"]
    assert (ang["app"]["bottles"], ang["app"]["match"], ang["lwin"]) == (6, "name", "1011111")
    (wine_id, app_lwin), = ang["app"]["fix"]
    assert app_lwin == "1222222"
    assert r["totals"]["by_name"] == 1
    assert [b["cuvee"] for b in r["app_only"]] == ["Champans"]  # same appellation, another climat: not matched

    assert client.post("/api/bordeaux-index/use-lwin", json={"wine_id": wine_id, "lwin": ang["lwin"]}).json()["lwin"] == "1011111"
    assert lines(client)["ST_ANG"]["app"]["match"] == "lwin"  # matched by LWIN from now on
    assert client.post("/api/bordeaux-index/use-lwin", json={"wine_id": wine_id, "lwin": "12"}).status_code == 422


def test_nv_bottle_is_priced_from_bi(client, bi):
    from winelib_utils import update_market_prices as prices
    from db import get_session
    from main import app
    session = next(app.dependency_overrides[get_session]())
    gc = next(b for b in session.query(Bottle).all() if b.wine.cuvee == "Grande Cuvée")
    assert prices.price_bottle(gc, {}, log=lambda line: None, bi=prices.bi_quotes()) == 180  # last trade 1080 / 6
    assert gc.last_price_source == "Bordeaux Index"
    session.rollback()
    session.close()


def test_portfolio_is_shared_for_a_few_minutes(client, fetch_price, bi, monkeypatch):
    """The view and the market price button read BI's portfolio once; a price run (and Refresh) reads it again."""
    from winelib_utils import update_market_prices as prices
    reads = []
    monkeypatch.setattr(bi, "portfolio", lambda: reads.append(1) or PORTFOLIO)
    monkeypatch.setattr(prices, "api_key", lambda: None)
    monkeypatch.setattr(bi, "market_quote", lambda *key: None)
    bi.forget_portfolio()

    client.get("/api/bordeaux-index")
    gc = next(b for b in client.get("/api/cellar").json()["bottles"] if b["cuvee"] == "Grande Cuvée")
    assert fetch_price(gc['bottle_id'])["last_price_source"] == "Bordeaux Index"
    assert len(reads) == 1  # the button used the view's copy

    client.get("/api/bordeaux-index?refresh=true")
    assert len(reads) == 2
    assert prices.bi_quotes(refresh=True) and len(reads) == 3  # what a price run does first
