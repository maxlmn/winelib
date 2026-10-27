"""The wishlist: adding, editing and removing wines, what's already in the cellar, the market price against the
target, and its wines priced with the bottles."""
from datetime import date

from db import Bottle, Producer, Wine, WishlistItem


def seed(s):
    p = Producer(name="Clos Rougeard")
    s.add_all([Wine(producer=p, cuvee="Le Bourg", vintage="2016", type="Red", lwin="1012345"),
               Wine(producer=p, cuvee="Le Bourg", vintage="2017", type="Red", lwin="1012345"),
               Wine(producer=p, cuvee="Les Poyeux", vintage="2018", type="Red")])  # no LWIN
    s.flush()
    s.add(Bottle(wine_id=2, qty=1, location="H1", price=300, currency="EUR"))


def test_add_edit_remove(client):
    r = client.post("/api/wishlist", json={"wine_id": 1, "target_price": 250, "currency": "eur", "note": " For 2030 "})
    assert r.status_code == 200, r.text
    item = r.json()
    assert (item["producer"], item["cuvee"], item["vintage"]) == ("Clos Rougeard", "Le Bourg", "2016")
    assert (item["target_price"], item["currency"], item["note"], item["owned"]) == (250, "EUR", "For 2030", 0)
    assert item["added"] == date.today().isoformat()
    # The 2017 is in the cellar: any vintage of the cuvée counts once that's ticked
    item = client.put(f"/api/wishlist/{item['id']}", json={"any_vintage": True, "target_price": 250, "currency": "EUR"}).json()
    assert item["owned"] == 1 and item["note"] is None
    # Adding the same wine again updates its entry
    again = client.post("/api/wishlist", json={"wine_id": 1, "target_price": 200}).json()
    assert again["id"] == item["id"] and again["target_price"] == 200
    assert [i["wine_id"] for i in client.get("/api/wishlist").json()["items"]] == [1]
    assert client.get("/api/wines/1").json()["wishlist"]["id"] == item["id"]
    assert client.get("/api/wines/2").json()["wishlist"] is None
    assert client.delete(f"/api/wishlist/{item['id']}").json() == {"deleted": item["id"]}
    assert client.get("/api/wishlist").json()["items"] == []
    assert client.post("/api/wishlist", json={"wine_id": 999}).status_code == 404


def test_market_price_against_the_target(client, monkeypatch):
    from tasks import update_market_prices as prices
    monkeypatch.setattr(prices, "api_key", lambda: "k")
    monkeypatch.setattr(prices, "fetch_winelabs", lambda lwin, vintage, target_currency="GBP", log=print:
                        {"price": 240.0, "currency": target_currency, "sales": 9})
    item = client.post("/api/wishlist", json={"wine_id": 1, "target_price": 250, "currency": "EUR"}).json()
    item = client.post(f"/api/wishlist/{item['id']}/price").json()
    assert item["market"]["price"] == 240 and item["market"]["source"] == "WineLabs.ai"
    assert item["below_target"] is True
    # A magnum: twice a bottle's price; a change of size forgets the old one
    item = client.put(f"/api/wishlist/{item['id']}", json={"bottle_size": "150cl", "target_price": 400, "currency": "EUR"}).json()
    assert item["market"] is None
    item = client.post(f"/api/wishlist/{item['id']}/price").json()
    assert item["market"]["price"] == 480 and item["below_target"] is False
    # Without an LWIN there's nothing to ask
    other = client.post("/api/wishlist", json={"wine_id": 3}).json()
    assert client.post(f"/api/wishlist/{other['id']}/price").status_code == 400


def session_of(client):
    import db
    return next(client.app.dependency_overrides[db.get_session]())


def test_priced_with_the_bottles(client):
    """The Market prices task and the nightly run take the wishlist's wines with an LWIN."""
    from tasks import update_market_prices as prices
    s = session_of(client)
    assert {i.wine_id for i in prices.wishlist_items(s, max_age_days=0)} == {1}  # wine 3 has no LWIN
    assert prices.wishlist_items(s) == []  # wine 1 priced today (above)


def test_a_merged_wine_keeps_its_entry(client):
    from tasks.merge_cuvees import carry
    s = session_of(client)
    w3 = s.get(Wine, 3)
    twin = Wine(producer_id=w3.producer_id, cuvee="Les Poyeux", vintage="2018", type="Red")
    s.add(twin)
    s.flush()
    carry(twin, w3)
    s.delete(w3)
    s.commit()
    assert s.query(WishlistItem).filter_by(wine_id=twin.id).count() == 1
