"""Global search."""
from db import Appellation, Place, Producer, Region, Varietal, Vineyard, Wine


def seed(s):
    loire = Region(name="Loire", country="France")
    rougeard = Producer(name="Clos Rougeard", region_obj=loire, village="Chacé")
    saumur = Appellation(name="Saumur-Champigny", region_obj=loire, type="AOP")
    s.add_all([
        Wine(producer=rougeard, cuvee="Le Bourg", vintage="2016", appellation=saumur, region_obj=loire),
        Wine(producer=rougeard, cuvee="Les Poyeux", vintage="2017", appellation=saumur, region_obj=loire),
        Producer(name="Domaine du Clos Naudin", region_obj=loire),
        Producer(name="Château L'Évangile"),
        Place(name="Odette", city="Singapore", country="Singapore", michelin_stars=3),
        Place(name="Le Clos des Sens", city="Annecy", michelin_stars=3),
        Vineyard(name="Les Poyeux", village="Saumur", region_obj=loire),
        Varietal(name="Cabernet Franc", aliases="Breton"),
    ])


def titles(client, q, kind=None):
    results = client.get("/api/search", params={"q": q}).json()["results"]
    return [r["title"] for r in results if kind is None or r["kind"] == kind]


def test_short_queries_return_nothing(client):
    assert titles(client, "c") == []


def test_names_starting_with_the_query_come_first(client):
    assert titles(client, "clos", "producer") == ["Clos Rougeard", "Domaine du Clos Naudin"]
    assert titles(client, "clos", "place") == ["Le Clos des Sens"]


def test_wine_words_match_across_producer_cuvee_and_vintage(client):
    assert titles(client, "rougeard bourg 2016", "wine") == ["Clos Rougeard Le Bourg 2016"]
    assert titles(client, "poyeux", "wine") == ["Clos Rougeard Les Poyeux 2017"]
    assert titles(client, "champigny 2016", "wine") == ["Clos Rougeard Le Bourg 2016"]


def test_every_kind_and_subtitles(client):
    results = client.get("/api/search", params={"q": "POYEUX"}).json()["results"]
    assert {r["kind"] for r in results} == {"wine", "vineyard"}
    odette = client.get("/api/search", params={"q": "singapore"}).json()["results"][0]
    assert (odette["kind"], odette["title"], odette["sub"]) == ("place", "Odette", "Singapore · Singapore · ★★★")
    assert titles(client, "champigny", "appellation") == ["Saumur-Champigny"]
    subs = {r["kind"]: r["sub"] for r in client.get("/api/search", params={"q": "rougeard"}).json()["results"]}
    assert subs["producer"] == "Loire, France · Chacé"  # a region is named with its country
    assert subs["wine"] == "Saumur-Champigny · Loire, France"
    regions = {r["kind"]: r["region"] for r in client.get("/api/search", params={"q": "rougeard"}).json()["results"]}
    assert regions == {"producer": "Loire", "wine": "Loire"}  # for the colour dot


def test_regions_and_grapes_are_found(client):
    assert titles(client, "loir", "region") == ["Loire"]
    region = next(r for r in client.get("/api/search", params={"q": "loir"}).json()["results"] if r["kind"] == "region")
    assert region["sub"] == "France"
    assert titles(client, "cab franc", "grape") == ["Cabernet Franc"]
    assert titles(client, "breton", "grape") == ["Cabernet Franc"]  # by alias


def test_accents_case_and_punctuation_are_ignored(client):
    assert titles(client, "evangile", "producer") == ["Château L'Évangile"]
    assert titles(client, "chateau l evangile", "producer") == ["Château L'Évangile"]
    assert titles(client, "CHACE", "producer") == []  # the village (Chacé) is shown, not searched
    assert titles(client, "saumur champigny 2016", "wine") == ["Clos Rougeard Le Bourg 2016"]
