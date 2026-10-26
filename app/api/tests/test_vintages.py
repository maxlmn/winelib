"""Vintage pages: GET /api/vintages and /api/vintages/{year}."""
from db import Bottle, Producer, Region, TastingNote, Wine
from conftest import rp


def seed(s):
    loire, rhone = Region(name="Loire", country="France", color="#a00"), Region(name="Rhône", country="France")
    rougeard, jamet = Producer(name="Clos Rougeard"), Producer(name="Domaine Jamet")
    bourg = Wine(producer=rougeard, cuvee="Le Bourg", vintage="2016", type="Red", region_obj=loire, scores=rp("(95-97)"))
    poyeux = Wine(producer=rougeard, cuvee="Les Poyeux", vintage="2016", type="Red", region_obj=loire, scores=rp("93"))
    rotie = Wine(producer=jamet, cuvee="", vintage="2016", type="Red", region_obj=rhone, scores=rp("98"))  # review only
    s.add_all([bourg, poyeux, rotie,
               Wine(producer=jamet, cuvee="", vintage="2019", type="Red", region_obj=rhone),
               Wine(producer=jamet, cuvee="", vintage="2010", type="Red", region_obj=rhone),
               Wine(producer=rougeard, cuvee="Brézé", vintage=None, type="White", region_obj=loire)])
    s.flush()
    line = Bottle(wine=poyeux, qty=1, location="H2")
    s.add_all([Bottle(wine=bourg, qty=2, location="H1"), line])
    s.flush()
    line.qty = 0
    s.add(TastingNote(bottle=line, rating=94, notes="Fine"))


def test_list(client):
    rows = client.get("/api/vintages").json()
    assert [r["vintage"] for r in rows] == ["2019", "2016", "2010", "NV"]
    assert rows[1] == {"vintage": "2016", "wines": 3, "bottles": 2, "tastings": 1,
                       # only regions with bottles or tastings: the bars' segments
                       "regions": [{"region": "Loire", "bottles": 2, "tastings": 1}]}


def test_detail(client):
    v = client.get("/api/vintages/2016").json()
    assert (v["vintage"], v["prev"], v["next"]) == ("2016", "2010", "2019")
    assert v["stats"]["bottles"] == 2 and v["stats"]["tastings"] == 1 and v["stats"]["wines"] == 3
    assert v["stats"]["producers"] == 2 and v["stats"]["score_count"] == 3 and v["stats"]["critic"] == "Robert Parker"
    assert v["stats"]["score_mine"] == 94.0  # (95 + 93) / 2: the Côte-Rôtie is a review only
    assert [(b["producer"], b["score"]) for b in v["best"]] == [("Domaine Jamet", "98"), ("Clos Rougeard", "(95-97)"),
                                                             ("Clos Rougeard", "93")]
    assert [r["name"] for r in v["regions"]] == ["Loire", "Rhône"]  # yours first
    assert v["regions"][0] == {"name": "Loire", "color": "#a00", "wines": 2, "bottles": 2, "tastings": 1}
    assert [t["notes"] for t in v["tastings"]] == ["Fine"]
    assert {w["cuvee"] for w in v["wines"]} == {"Le Bourg", "Les Poyeux", ""}


def test_nv_and_missing(client):
    nv = client.get("/api/vintages/nv").json()
    assert nv["vintage"] == "NV" and nv["prev"] is None and [w["cuvee"] for w in nv["wines"]] == ["Brézé"]
    assert client.get("/api/vintages/1900").status_code == 404
    assert client.get("/api/vintages/abc").status_code == 404


def test_the_preferred_critic_ranks(client):
    # Vinous rates the Poyeux above Le Bourg: with Vinous preferred, best rated and the stats follow it
    client.post("/api/wines/1/scores", json={"critic": "Vinous", "score": "91"})
    client.post("/api/wines/2/scores", json={"critic": "Vinous", "score": "95"})
    current = client.get("/api/settings").json()
    assert client.put("/api/settings", json={**current, "preferred_critic": "Vinous"}).status_code == 200
    v = client.get("/api/vintages/2016").json()
    assert v["stats"]["critic"] == "Vinous" and v["stats"]["score_count"] == 2
    assert [(b["cuvee"], b["score"]) for b in v["best"]] == [("Les Poyeux", "95"), ("Le Bourg", "91")]
    assert v["best"][0]["scores"] == "VI 95 · RP 93"  # every critic shown, the preferred one first
    bottle = next(b for b in client.get("/api/cellar").json()["bottles"] if b["wine_id"] == 1)
    assert bottle["score"] == "91"  # the cellar sorts by it too
    client.put("/api/settings", json={**current, "preferred_critic": "Robert Parker"})
