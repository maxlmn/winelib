"""Style tags: set on a wine by hand, or picked in its tastings, gathered when shown (never copied): on the wine page
with counts, on the cellar's bottles for the filters; the vocabulary and the tags in use."""
from db import Bottle, Producer, Wine


def seed(s):
    p = Producer(name="Domaine Huet")
    mont = Wine(producer=p, cuvee="Le Mont Sec", vintage="2019", type="White")
    mont18 = Wine(producer=p, cuvee="Le Mont Sec", vintage="2018", type="White")
    s.add_all([p, mont, mont18])
    s.flush()
    s.add_all([Bottle(wine_id=mont.id, qty=3, location="H1"), Bottle(wine_id=mont18.id, qty=1, location="H1")])


def ids(client):
    def wine(q):
        return next(r["id"] for r in client.get("/api/search", params={"q": q}).json()["results"] if r["kind"] == "wine")
    w19, w18 = wine("mont sec 2019"), wine("mont sec 2018")
    bottle = next(b["bottle_id"] for b in client.get(f"/api/wines/{w19}").json()["cellar"] if b["wine_id"] == w19)
    return w19, w18, bottle


def tasting(client, bottle, styles, day="2026-10-01"):
    r = client.post("/api/tastings", json={"source": "cellar", "bottle_id": bottle, "consume": False, "date": day,
                                           "styles": styles})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_set_tasted_and_gathered(client):
    w19, w18, bottle = ids(client)
    # set by hand: cleaned (trimmed, lower case, once)
    r = client.put(f"/api/wines/{w19}/tags", json={"tags": ["Mineral", " for  ageing ", "mineral", ""]})
    assert [t["tag"] for t in r.json()["tags"]] == ["for ageing", "mineral"]
    # tasted twice as fresh, once as mineral too
    first = tasting(client, bottle, ["fresh", "Mineral"])
    tasting(client, bottle, ["fresh"], "2026-10-05")
    tags = {t["tag"]: t for t in client.get(f"/api/wines/{w19}").json()["tags"]}
    assert (tags["mineral"]["set"], tags["mineral"]["tastings"]) == (True, 1)
    assert (tags["fresh"]["set"], tags["fresh"]["tastings"]) == (False, 2)
    assert client.get(f"/api/forms/tastings/{first}").json()["styles"] == ["fresh", "mineral"]

    # the other vintage suggests them; the cellar's bottles carry them for the filters
    assert client.get(f"/api/wines/{w18}").json()["cuvee_tags"] == ["for ageing", "fresh", "mineral"]
    lines = {b["wine_id"]: b["tags"] for b in client.get("/api/cellar").json()["bottles"]}
    assert set(lines[w19]) == {"for ageing", "mineral", "fresh"} and lines[w18] == []

    # the vocabulary, and what's in use
    t = client.get("/api/tags").json()
    assert "fresh" in t["vocabulary"] and {"tag": "mineral", "wines": 1} in t["used"]

    # deleting a tasting drops its tags (nothing was copied onto the wine)
    client.delete(f"/api/tastings/{first}")
    tags = {t["tag"]: t for t in client.get(f"/api/wines/{w19}").json()["tags"]}
    assert tags["fresh"]["tastings"] == 1 and tags["mineral"]["tastings"] == 0 and tags["mineral"]["set"]

    # a tasting saved without styles keeps its own (an older client); an empty list clears them
    second = next(x["id"] for x in client.get("/api/tastings").json()["tastings"] if x["wine_id"] == w19)
    form = client.get(f"/api/forms/tastings/{second}").json()
    keep = {"date": form["date"], "rating": None, "glasses": 1, "sequence": 1}
    client.put(f"/api/tastings/{second}", json=keep)
    assert client.get(f"/api/forms/tastings/{second}").json()["styles"] == ["fresh"]
    client.put(f"/api/tastings/{second}", json={**keep, "styles": []})
    assert client.get(f"/api/forms/tastings/{second}").json()["styles"] == []
