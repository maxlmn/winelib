"""Lists: entries of three kinds (a wine, a cuvée any vintage, a producer), mixed; each ticked when tasted (that
vintage, any vintage, any wine) with the bottles owned apart; which lists a wine or a producer is on."""
from datetime import date

from db import Bottle, Producer, TastingNote, Wine


def seed(s):
    rougeard = Producer(name="Clos Rougeard")
    chave = Producer(name="Jean-Louis Chave")
    coche = Producer(name="Domaine Coche-Dury")
    bourg16 = Wine(producer=rougeard, cuvee="Le Bourg", vintage="2016", type="Red")
    bourg17 = Wine(producer=rougeard, cuvee="Le Bourg", vintage="2017", type="Red")
    poyeux = Wine(producer=rougeard, cuvee="Les Poyeux", vintage="2018", type="Red")
    florentin18 = Wine(producer=chave, cuvee="Clos Florentin", vintage="2018", type="Red")
    florentin19 = Wine(producer=chave, cuvee="Clos Florentin", vintage="2019", type="Red")
    s.add_all([rougeard, chave, coche, bourg16, bourg17, poyeux, florentin18, florentin19])
    s.flush()
    drunk = Bottle(wine_id=florentin19.id, qty=0, location="Consumed")  # the 2019 tasted, not the 2018
    s.add_all([drunk, Bottle(wine_id=bourg17.id, qty=2, location="H1")])  # the 2017 owned, not tasted
    s.flush()
    s.add(TastingNote(bottle_id=drunk.id, date=date(2026, 3, 1), rating=94))


def ids(client):
    def wine(q):
        return next(r["id"] for r in client.get("/api/search", params={"q": q}).json()["results"] if r["kind"] == "wine")
    def producer(q):
        return next(r["id"] for r in client.get("/api/search", params={"q": q}).json()["results"] if r["kind"] == "producer")
    return None, wine, producer


def test_a_mixed_list_and_its_ticks(client):
    _, wine, producer = ids(client)
    lst = client.post("/api/lists", json={"name": "Noble Rot Wines of The Decade", "source": "Noble Rot"}).json()["id"]
    add = lambda **b: client.post(f"/api/lists/{lst}/items", json=b).json()  # noqa: E731
    florentin = add(kind="wine", wine_id=wine("clos florentin 2018"), note="the 2018")
    florentin_any = add(kind="cuvee", wine_id=wine("clos florentin 2018"))
    bourg = add(kind="cuvee", wine_id=wine("le bourg 2016"))
    coche = add(kind="producer", producer_id=producer("coche-dury"))
    assert add(kind="wine", wine_id=wine("clos florentin 2018"))["existing"] is True  # once only

    d = client.get(f"/api/lists/{lst}").json()
    by_id = {i["id"]: i for i in d["items"]}
    # That vintage: the 2018 isn't tasted (the 2019 is)
    assert by_id[florentin["id"]]["tasted"] is False and by_id[florentin["id"]]["note"] == "the 2018"
    # Any vintage of the cuvée: the 2019 counts
    any_ = by_id[florentin_any["id"]]
    assert (any_["tasted"], any_["best_rating"], any_["last_tasted"]) == (True, 94, "2026-03-01")
    # Owned is apart from the tick: Le Bourg 2017 in the cellar, never tasted
    assert (by_id[bourg["id"]]["tasted"], by_id[bourg["id"]]["owned"]) == (False, 2)
    # A producer with nothing tasted
    assert by_id[coche["id"]]["tasted"] is False and by_id[coche["id"]]["wine"] is None
    assert (d["entries"], d["tasted"], d["owned"]) == (4, 1, 1)
    # The wines that count for each entry: that one; the cuvée's two vintages; none for a producer without wines
    assert len(by_id[florentin["id"]]["wine_ids"]) == 1 and len(by_id[florentin_any["id"]]["wine_ids"]) == 2
    assert by_id[coche["id"]]["wine_ids"] == []

    summary = next(x for x in client.get("/api/lists").json() if x["id"] == lst)
    assert [dot["tasted"] for dot in summary["dots"]] == [False, True, False, False]


def test_on_the_wine_and_producer_pages(client):
    _, wine, producer = ids(client)
    lst = client.post("/api/lists", json={"name": "Rougeard"}).json()["id"]
    client.post(f"/api/lists/{lst}/items", json={"kind": "cuvee", "wine_id": wine("le bourg 2016")})
    other = client.post("/api/lists", json={"name": "Loire producers"}).json()["id"]
    client.post(f"/api/lists/{other}/items", json={"kind": "producer", "producer_id": producer("rougeard")})
    # The 2017 is on "Rougeard" through its cuvée, on "Loire producers" through its producer
    on = client.get("/api/lists-of", params={"wine_id": wine("le bourg 2017")}).json()
    assert {(x["name"], x["as"]) for x in on} >= {("Rougeard", "cuvee"), ("Loire producers", "producer")}
    # Les Poyeux only through its producer
    on = client.get("/api/lists-of", params={"wine_id": wine("poyeux")}).json()
    assert [(x["name"], x["as"]) for x in on] == [("Loire producers", "producer")]
    # The producer: both lists
    on = client.get("/api/lists-of", params={"producer_id": producer("rougeard")}).json()
    assert {x["name"] for x in on} >= {"Rougeard", "Loire producers"}


def test_names_edits_and_removal(client):
    _, wine, _ = ids(client)
    assert client.post("/api/lists", json={"name": "rougeard"}).status_code == 409  # same name, any case
    lst = client.post("/api/lists", json={"name": "To edit"}).json()["id"]
    item = client.post(f"/api/lists/{lst}/items", json={"kind": "wine", "wine_id": wine("poyeux")}).json()["id"]
    client.put(f"/api/lists/{lst}/items/{item}", json={"note": "Magnum please"})
    assert client.get(f"/api/lists/{lst}").json()["items"][0]["note"] == "Magnum please"
    assert client.put(f"/api/lists/{lst}", json={"name": "Edited", "source": "Me"}).json() == {"id": lst}
    assert client.delete(f"/api/lists/{lst}/items/{item}").json() == {"deleted": item}
    assert client.post(f"/api/lists/{lst}/items", json={"kind": "glass", "wine_id": 1}).status_code == 422
    assert client.delete(f"/api/lists/{lst}").json() == {"deleted": lst}
    assert client.get(f"/api/lists/{lst}").status_code == 404


def test_a_deleted_wine_leaves_its_lists(client):
    lst = client.post("/api/lists", json={"name": "Gone"}).json()["id"]
    p = client.post("/api/producers", json={"name": "Short-lived", "region": None}).json()["id"]
    w = client.post("/api/wines", json={"producer": p, "cuvee": "Once", "vintage": "2020"}).json()["id"]
    client.post(f"/api/lists/{lst}/items", json={"kind": "wine", "wine_id": w})
    assert client.delete(f"/api/wines/{w}").status_code == 200
    assert client.get(f"/api/lists/{lst}").json()["entries"] == 0


def test_the_wishlist_is_a_list(client):
    first = client.post("/api/lists/wishlist").json()["id"]
    assert client.post("/api/lists/wishlist").json()["id"] == first  # made once
    lst = client.get(f"/api/lists/{first}").json()
    assert (lst["name"], lst["is_wishlist"]) == ("Wishlist", True)
