"""Bordeaux Index mixed cases (ASSORTMENTS): Guigal's Côte-Rôtie assortment case is three wines in the app."""
import pytest

from db import Bottle, Producer, Wine

PORTFOLIO = [
    {"portfolioRef": "ST_9", "lwin18": 107777720150300750, "productName": "E. Guigal, Cote Rotie, Assortment Case",
     "producer": "E. Guigal", "packSize": 3, "vintageYear": 2015, "quantity": 2, "costPrice": 3000, "size": 75,
     "bids": [{"price": 3300}], "lastTrade": {"price": 3600}},
]


def seed(s):
    p = Producer(name="E. Guigal")
    wines = [Wine(producer=p, cuvee=c, vintage="2015", type="Red", lwin=l)
             for c, l in (("La Landonne", "1011111"), ("La Mouline", "1022222"), ("La Turque", "1033333"),
                          ("Château d'Ampuis", "1044444"))]
    s.add_all(wines)
    s.flush()
    s.add_all([Bottle(wine_id=wines[0].id, qty=2, location="Bonded", price=400, currency="GBP"),
               Bottle(wine_id=wines[1].id, qty=2, location="Bonded", price=400, currency="GBP"),
               Bottle(wine_id=wines[2].id, qty=1, location="Bonded", price=400, currency="GBP"),
               Bottle(wine_id=wines[2].id, qty=1, location="H1", price=400, currency="GBP"),  # at home
               Bottle(wine_id=wines[3].id, qty=1, location="Bonded", price=100, currency="GBP")])  # not in the case


@pytest.fixture
def bi(monkeypatch):
    from tasks import bordeaux_index as bi
    for k in ("BI_EMAIL", "BI_PASSWORD", "BI_SALES_LEDGER", "BI_PURCHASE_LEDGER"):
        monkeypatch.setenv(k, "x")
    monkeypatch.setattr(bi, "portfolio", lambda: PORTFOLIO)
    bi.forget_portfolio()
    return bi


def test_assortment_case_matches_its_three_wines(client, bi):
    r = client.get("/api/bordeaux-index").json()
    line = r["lines"][0]
    assert line["bottles"] == 6 and line["app"]["match"] == "assortment" and line["app"]["bottles"] == 5
    assert line["app"]["parts"] == [{"name": "Landonne", "expected": 2, "held": 2},
                                    {"name": "Mouline", "expected": 2, "held": 2},
                                    {"name": "Turque", "expected": 2, "held": 1}]
    assert [b["cuvee"] for b in r["app_only"]] == ["Château d'Ampuis"]


def test_assortment_price_isnt_one_wines(bi):
    assert bi.quotes([bi.line(it) for it in PORTFOLIO]) == {}
