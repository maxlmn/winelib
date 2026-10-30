"""Fill from text (tasks/from_text.py): a purchase read from a pasted email or invoice against the database. Run from
app/api:  pytest"""
import settings
from db import Appellation, Bottle, Producer, Region, Vineyard, Wine

IDEALWINE = """Bonjour M. Lemeunier, Félicitations ! Vous venez de remporter l'enchère du lot N°2823982 de la vente N°12751 du
29/10/2026 organisée par INTERNATIONAL WINE AUCTION (Groupe iDealwine). Pour rappel, voici le détail de votre commande :
| | Description du lot : 2 Bouteilles Château Latour 1er Grand Cru Classé Rouge 1986 Couleur : Rouge Millésime : 1986 Pays/Région : Bordeaux Appellation : Pauillac Classement : 1er Grand Cru Classé |

Prix d'adjudication : 680,00 €

L'équipe d'iDealwine."""

SHOP = """Order confirmation #4411 — October 12, 2026
Thank you for your order from Clos Shop.
3 x Clos Rougeard Le Bourg 2019 Saumur-Champigny   Unit price: EUR 210.00
Total: EUR 630.00"""


def seed(s):
    bordeaux, loire = Region(name="Bordeaux"), Region(name="Loire")
    pauillac = Appellation(name="Pauillac", region_obj=bordeaux)
    sc = Appellation(name="Saumur-Champigny", region_obj=loire)
    latour, rougeard = Producer(name="Chateau Latour", region_obj=bordeaux), Producer(name="Clos Rougeard")
    enclos = Vineyard(name="Château Latour", region_obj=bordeaux)
    w85 = Wine(producer=latour, cuvee="Premier Grand Cru Classé", vintage="1985", type="Red", appellation=pauillac,
               region_obj=bordeaux, vineyard=enclos)
    bourg = Wine(producer=rougeard, cuvee="Le Bourg", vintage="2019", type="Red", appellation=sc, region_obj=loire)
    s.add_all([w85, bourg, Bottle(wine=w85, qty=1, location="H1", vendor="Idealwine")])


def test_an_auction_email(client):
    r = client.post("/api/lookups/from-text", json={"text": IDEALWINE})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["producer"]["name"] == "Chateau Latour" and d["vintage"] == "1986" and d["type"] == "Red"
    assert d["cuvee"] == "Premier Grand Cru Classé" and d["appellation"]["name"] == "Pauillac"
    assert d["wine_id"] is None and d["like_id"]  # not yet in WineLib: a new vintage of the 1985
    assert (d["qty"], d["price"], d["currency"], d["price_total"]) == (2, 340.0, "EUR", 680.0)  # the lot's price, halved
    assert (d["purchase_date"], d["vendor"]) == ("2026-10-29", "Idealwine")


def test_a_shop_order(client):
    d = client.post("/api/lookups/from-text", json={"text": SHOP}).json()
    assert (d["producer"]["name"], d["cuvee"], d["vintage"]) == ("Clos Rougeard", "Le Bourg", "2019")
    assert d["wine_id"]  # that very wine is in WineLib
    assert (d["qty"], d["price"], d["currency"], d["price_total"]) == (3, 210.0, "EUR", None)  # the unit price
    assert d["purchase_date"] == "2026-10-12"


def test_a_premium_vendor_is_found_and_nothing_is_refused(client, monkeypatch):
    monkeypatch.setattr(settings.current, "vendor_premiums", {"Hart Davis Hart": 25})
    d = client.post("/api/lookups/from-text", json={"text": "Won at HART DAVIS HART: 1 bottle Clos Rougeard Le Bourg 2019"}).json()
    assert d["vendor"] == "Hart Davis Hart" and d["qty"] == 1
    magnums = client.post("/api/lookups/from-text", json={"text": "3 magnums Clos Rougeard Le Bourg 2019"}).json()
    assert (magnums["qty"], magnums["size"]) == (3, "150cl")
    assert client.post("/api/lookups/from-text", json={"text": "Thanks for shopping with us"}).status_code == 422
