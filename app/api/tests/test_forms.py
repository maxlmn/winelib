"""Form writes (create / update / delete) and the lookups behind them. Run from app/api:  pytest"""
from datetime import date

from db import Appellation, Bottle, Place, Producer, Region, RestaurantVisit, TastingNote, Varietal, Vineyard, Wine

import db
from main import app

IDS = {}


def seed(s):
    loire = Region(name="Loire", color="#a4c96b")
    rhone = Region(name="Rhône")
    chinon = Appellation(name="Chinon", region_obj=loire)
    cote_rotie = Appellation(name="Côte-Rôtie", region_obj=rhone)
    cf = Varietal(name="Cabernet Franc", aliases="Breton, Bouchet")
    coulaine = Producer(name="Chateau de Coulaine", region_obj=loire)
    empty = Producer(name="Domaine Vide", region_obj=loire)
    picasses = Vineyard(name="Les Picasses", region_obj=loire, sub_region="Touraine", village="Chinon")
    red = Wine(producer=coulaine, cuvee="Les Picasses", vintage="2020", type="Red", region_obj=loire,
               appellation=chinon, varietal=cf, vineyard=picasses)
    rotie = Wine(producer=Producer(name="Jamet", region_obj=rhone), cuvee="", vintage="2017", type="Red",
                 region_obj=rhone, appellation=cote_rotie)
    stocked = Bottle(wine=red, location="H2", qty=3, price=40, currency="SGD", bottle_size="75cl")
    last = Bottle(wine=red, location="H3", qty=1, price=40, currency="SGD")
    gone = Bottle(wine=rotie, location="H4", qty=0, price=90, currency="EUR")
    home = Place(name="@Home", city="Singapore", country="Singapore", type="Home")
    unused = Place(name="Nowhere Bar")
    s.add_all([empty, stocked, last, gone, home, unused])
    s.flush()
    s.add(RestaurantVisit(date=date(2024, 5, 1), place=home, notes="Dinner"))
    s.add(TastingNote(bottle=gone, date=date(2024, 1, 1), place=home, location="@Home"))
    s.flush()
    IDS.update(loire=loire.id, rhone=rhone.id, chinon=chinon.id, cote_rotie=cote_rotie.id, cf=cf.id, coulaine=coulaine.id, empty=empty.id,
               picasses=picasses.id, red=red.id, rotie=rotie.id, stocked=stocked.id, last=last.id, gone=gone.id,
               home=home.id, unused=unused.id)


def fresh_session():
    return next(app.dependency_overrides[db.get_session]())


def get(model, id_):
    session = fresh_session()
    return session, session.get(model, id_)


def query(model, **by):
    return fresh_session().query(model).filter_by(**by).all()


def detail(r):
    return r.json()["detail"]


# --- Producers --------------------------------------------------------------------------------

def test_producer_create_with_existing_and_new_region(client):
    r = client.post("/api/producers", json={"name": " Domaine Neuf ", "region": IDS["loire"], "type": "domaine",
                                            "village": "", "website": "https://neuf.fr"})
    assert r.status_code == 201
    _, p = get(Producer, r.json()["id"])
    assert (p.name, p.region_obj.name, p.type, p.village, p.website) == ("Domaine Neuf", "Loire", "domaine", None, "https://neuf.fr")

    r = client.post("/api/producers", json={"name": "Bodega Nueva", "region": {"name": "Rioja"}})
    _, p = get(Producer, r.json()["id"])
    assert p.region_obj.name == "Rioja"
    # get-or-create: the second time reuses the region
    r = client.post("/api/producers", json={"name": "Bodega Otra", "region": {"name": "Rioja"}})
    assert len(query(Region, name="Rioja")) == 1


def test_producer_validation(client):
    r = client.post("/api/producers", json={"name": "chateau de coulaine"})
    assert r.status_code == 409 and "already exists" in detail(r)
    assert client.post("/api/producers", json={"name": "  "}).status_code == 422
    assert client.post("/api/producers", json={"name": "X", "type": "coop"}).status_code == 422
    assert client.post("/api/producers", json={"name": "X", "region": 9999}).status_code == 404


def test_producer_update_and_delete(client):
    r = client.put(f"/api/producers/{IDS['empty']}", json={"name": "Domaine Plein", "region": None, "notes": "Hi"})
    assert r.status_code == 200
    _, p = get(Producer, IDS["empty"])
    assert (p.name, p.region_id, p.notes) == ("Domaine Plein", None, "Hi")
    # keeping its own name is not a conflict
    assert client.put(f"/api/producers/{IDS['empty']}", json={"name": "Domaine Plein"}).status_code == 200
    assert client.put(f"/api/producers/{IDS['empty']}", json={"name": "Jamet"}).status_code == 409

    r = client.delete(f"/api/producers/{IDS['coulaine']}")
    assert r.status_code == 409 and "1 wine" in detail(r)
    assert client.delete(f"/api/producers/{IDS['empty']}").json() == {"deleted": IDS["empty"]}
    assert client.get(f"/api/forms/producers/{IDS['empty']}").status_code == 404


# --- Wines ------------------------------------------------------------------------------------

def test_wine_create_existing_refs(client):
    r = client.post("/api/wines", json={
        "producer": IDS["coulaine"], "cuvee": "Les Picasses", "vintage": "2021", "type": "Red", "region": IDS["loire"],
        "appellation": IDS["chinon"], "varietal": IDS["cf"], "vineyard": IDS["picasses"], "disgorgement_date": "Oct 2024",
        "drink_window_start": 0, "drink_window_end": 2035, "lwin": ""})
    assert r.status_code == 201
    _, w = get(Wine, r.json()["id"])
    assert (w.producer_id, w.appellation_id, w.varietal_id, w.vineyard_id) == (IDS["coulaine"], IDS["chinon"], IDS["cf"], IDS["picasses"])
    assert w.disgorgement_date is None  # only kept for Bubbles
    assert (w.drink_window_start, w.drink_window_end, w.lwin) == (None, 2035, None)


def test_wine_create_inline_new_producer_appellation_varietal(client):
    r = client.post("/api/wines", json={
        "producer": {"name": "Domaine Inline", "region": IDS["rhone"]}, "cuvee": "Brut", "vintage": "NV",
        "type": "Bubbles", "disgorgement_date": "Jan 2025", "region": IDS["rhone"],
        "appellation": {"name": "Saint-Péray"}, "varietal": {"name": "Marsanne"}})
    assert r.status_code == 201
    _, w = get(Wine, r.json()["id"])
    assert w.producer.name == "Domaine Inline" and w.producer.region_obj.name == "Rhône"
    assert w.appellation.name == "Saint-Péray" and w.appellation.region_obj.name == "Rhône"  # takes the wine's region
    assert w.varietal.name == "Marsanne" and w.disgorgement_date == "Jan 2025"


def test_wine_named_refs_reuse_existing_rows(client):
    r = client.post("/api/wines", json={
        "producer": {"name": "CHATEAU DE COULAINE"}, "type": "White", "appellation": {"name": "chinon"},
        "varietal": {"name": "cabernet franc"}, "region": {"name": "Loire"}})
    _, w = get(Wine, r.json()["id"])
    assert (w.producer_id, w.appellation_id, w.varietal_id, w.region_id) == (IDS["coulaine"], IDS["chinon"], IDS["cf"], IDS["loire"])
    assert len(query(Producer, name="CHATEAU DE COULAINE")) == 0


def test_wine_validation(client):
    assert client.post("/api/wines", json={"cuvee": "No producer"}).status_code == 422
    assert client.post("/api/wines", json={"producer": IDS["coulaine"], "type": "Blue"}).status_code == 422
    assert client.post("/api/wines", json={"producer": {"name": ""}}).status_code == 422
    r = client.post("/api/wines", json={"producer": 9999})
    assert r.status_code == 404 and "Producer" in detail(r)


def test_wine_update_and_delete(client):
    r = client.put(f"/api/wines/{IDS['rotie']}", json={
        "producer": {"name": "Jamet"}, "vintage": "2018", "type": "Red", "region": IDS["rhone"], "appellation": IDS["cote_rotie"]})
    assert r.status_code == 200
    _, w = get(Wine, IDS["rotie"])
    assert (w.vintage, w.appellation_id, w.cuvee) == ("2018", IDS["cote_rotie"], "")  # no name: '', as the rest of the cellar

    r = client.delete(f"/api/wines/{IDS['red']}")
    assert r.status_code == 409 and "bottles" in detail(r)
    new = client.post("/api/wines", json={"producer": IDS["coulaine"], "cuvee": "Temp"}).json()["id"]
    assert client.delete(f"/api/wines/{new}").json() == {"deleted": new, "producer_id": IDS["coulaine"]}


# --- Bottles ----------------------------------------------------------------------------------

def test_bottle_create_for_existing_and_new_wine(client):
    r = client.post("/api/bottles", json={
        "wine": IDS["red"], "qty": 6, "bottle_size": "150cl", "location": "WB3", "price": 80, "currency": "EUR",
        "vendor": "IDW", "provenance": "", "purchase_date": "2025-03-01", "last_price": 0, "last_price_date": None})
    assert r.status_code == 201 and r.json()["wine_id"] == IDS["red"]
    _, b = get(Bottle, r.json()["id"])
    assert (b.qty, b.bottle_size, b.location, b.price, b.currency, b.purchase_date) == (6, "150cl", "WB3", 80, "EUR", date(2025, 3, 1))
    assert (b.provenance, b.last_price) == (None, None)

    r = client.post("/api/bottles", json={"wine": {"producer": {"name": "Clos Rougeard"}, "cuvee": "Le Bourg",
                                                    "vintage": "2015", "type": "Red", "region": IDS["loire"]}})
    _, b = get(Bottle, r.json()["id"])
    assert b.wine.producer.name == "Clos Rougeard" and (b.qty, b.bottle_size, b.currency) == (1, "75cl", "SGD")


def test_bottle_validation(client):
    r = client.post("/api/bottles", json={"wine": IDS["red"], "currency": "JPY"})
    assert r.status_code == 422 and "currency" in str(detail(r))
    assert client.post("/api/bottles", json={"wine": IDS["red"], "qty": -1}).status_code == 422
    assert client.post("/api/bottles", json={"wine": IDS["red"], "price": -5}).status_code == 422
    assert client.post("/api/bottles", json={"qty": 1}).status_code == 422


def test_bottle_update_and_delete(client):
    r = client.put(f"/api/bottles/{IDS['last']}", json={
        "wine": IDS["red"], "qty": 2, "location": "H5", "price": 42, "currency": "SGD", "last_price": 55,
        "last_price_date": "2025-06-01", "last_price_source": "wine-searcher"})
    assert r.status_code == 200
    _, b = get(Bottle, IDS["last"])
    assert (b.qty, b.location, b.last_price, b.last_price_source) == (2, "H5", 55, "wine-searcher")

    r = client.delete(f"/api/bottles/{IDS['gone']}")
    assert r.status_code == 409 and "tasting" in detail(r)
    new = client.post("/api/bottles", json={"wine": IDS["red"]}).json()["id"]
    assert client.delete(f"/api/bottles/{new}").json() == {"deleted": new, "wine_id": IDS["red"]}


# --- Tastings ---------------------------------------------------------------------------------

def test_tasting_from_cellar_consumes_a_bottle(client):
    r = client.post("/api/tastings", json={"source": "cellar", "bottle_id": IDS["stocked"], "consume": True,
                                           "date": "2025-02-01", "place": IDS["home"], "rating": 94, "glasses": 2.5,
                                           "sequence": 2, "tags": "Dinner", "notes": "Lovely"})
    assert r.status_code == 201
    out = r.json()
    assert (out["bottle_id"], out["wine_id"]) == (IDS["stocked"], IDS["red"])
    _, tn = get(TastingNote, out["id"])
    assert (tn.place_id, tn.location, tn.rating, tn.glasses, tn.sequence, tn.notes) == (IDS["home"], "@Home", 94, 2.5, 2, "Lovely")
    assert tn.bottle.qty == 2

    client.post("/api/tastings", json={"source": "cellar", "bottle_id": IDS["stocked"], "consume": False, "date": "2025-02-02"})
    _, b = get(Bottle, IDS["stocked"])
    assert b.qty == 2


def test_tasting_from_cellar_never_goes_below_zero(client):
    client.post("/api/tastings", json={"source": "cellar", "bottle_id": IDS["gone"], "date": "2025-02-01"})
    _, b = get(Bottle, IDS["gone"])
    assert b.qty == 0


def test_tasting_other_wine_creates_an_ad_hoc_bottle(client):
    r = client.post("/api/tastings", json={
        "source": "other", "wine": IDS["rotie"], "date": "2025-03-01", "place": {"name": "Odette", "city": "Singapore",
                                                                                  "country": "Singapore", "type": "Restaurant"},
        "bottle": {"bottle_size": "75cl", "price": 300, "currency": "SGD", "vendor": "Odette", "provenance": "Ad-Hoc",
                   "purchase_date": "2025-03-01"}})
    assert r.status_code == 201
    _, tn = get(TastingNote, r.json()["id"])
    b = tn.bottle
    assert (b.wine_id, b.qty, b.location, b.price, b.vendor, b.provenance) == (IDS["rotie"], 0, "Consumed", 300, "Odette", "Ad-Hoc")
    assert (tn.place.name, tn.place.type, tn.location) == ("Odette", "Restaurant", "Odette")
    assert (tn.glasses, tn.sequence, tn.rating) == (1.0, 1, None)  # the defaults; no invented score

    # the same new place typed again is reused
    r = client.post("/api/tastings", json={"source": "other", "wine": IDS["rotie"], "date": "2025-03-02", "place": {"name": "odette"}})
    assert len(query(Place, name="Odette")) == 1
    _, tn = get(TastingNote, r.json()["id"])
    assert tn.place.name == "Odette" and tn.bottle.provenance == "Ad-Hoc"


def test_tasting_other_wine_with_new_wine_and_producer(client):
    r = client.post("/api/tastings", json={
        "source": "other", "date": "2025-04-01",
        "wine": {"producer": {"name": "Domaine du Tasting", "region": {"name": "Jura"}}, "cuvee": "Savagnin",
                 "vintage": "2019", "type": "White", "region": {"name": "Jura"}, "appellation": {"name": "Arbois"}}})
    assert r.status_code == 201
    _, tn = get(TastingNote, r.json()["id"])
    w = tn.bottle.wine
    assert (w.producer.name, w.producer.region_obj.name, w.appellation.name, w.appellation.region_obj.name) == (
        "Domaine du Tasting", "Jura", "Arbois", "Jura")
    assert tn.location == "Unknown" and tn.place_id is None


def test_tasting_validation(client):
    r = client.post("/api/tastings", json={"source": "cellar", "date": "2025-01-01"})
    assert r.status_code == 422 and "bottle" in detail(r)
    r = client.post("/api/tastings", json={"source": "other", "date": "2025-01-01"})
    assert r.status_code == 422 and "wine" in detail(r)
    assert client.post("/api/tastings", json={"source": "cellar", "bottle_id": IDS["stocked"], "date": "2025-01-01",
                                              "rating": 40}).status_code == 422
    assert client.post("/api/tastings", json={"source": "cellar", "bottle_id": IDS["stocked"]}).status_code == 422
    assert client.post("/api/tastings", json={"source": "wine", "date": "2025-01-01"}).status_code == 422


def test_tasting_update_edits_note_and_bottle_details(client):
    tid = client.post("/api/tastings", json={"source": "other", "wine": IDS["red"], "date": "2025-05-01"}).json()["id"]
    r = client.put(f"/api/tastings/{tid}", json={
        "date": "2025-05-02", "place": IDS["home"], "rating": 91, "glasses": 1.5, "notes": "Edited",
        "bottle": {"bottle_size": "37.5cl", "price": 25, "currency": "EUR", "vendor": "Shop", "provenance": "Gift",
                   "purchase_date": None}})
    assert r.status_code == 200
    _, tn = get(TastingNote, tid)
    assert (tn.date, tn.location, tn.rating, tn.notes) == (date(2025, 5, 2), "@Home", 91, "Edited")
    assert (tn.bottle.bottle_size, tn.bottle.price, tn.bottle.currency, tn.bottle.provenance) == ("37.5cl", 25, "EUR", "Gift")
    form = client.get(f"/api/forms/tastings/{tid}").json()
    assert form["place"]["name"] == "@Home" and form["wine"]["id"] == IDS["red"]


def test_tasting_delete(client):
    r = client.post("/api/tastings", json={"source": "other", "wine": IDS["red"], "date": "2025-06-01"}).json()
    out = client.delete(f"/api/tastings/{r['id']}").json()
    assert out["bottle_deleted"] is True  # its ad-hoc bottle goes too
    _, b = get(Bottle, r["bottle_id"])
    assert b is None

    r = client.post("/api/tastings", json={"source": "cellar", "bottle_id": IDS["stocked"], "date": "2025-06-02"}).json()
    out = client.delete(f"/api/tastings/{r['id']}").json()
    assert out["bottle_deleted"] is False
    _, b = get(Bottle, IDS["stocked"])
    assert b is not None
    assert client.delete(f"/api/tastings/{r['id']}").status_code == 404


# --- Places and visits ------------------------------------------------------------------------

def test_place_create_update_delete(client):
    r = client.post("/api/places", json={"name": "Le Bistrot", "city": "Paris", "country": "France", "type": "Bistro",
                                         "michelin_stars": 1, "lat": 48.85, "lng": 0})
    assert r.status_code == 201
    pid = r.json()["id"]
    _, p = get(Place, pid)
    assert (p.city, p.michelin_stars, p.lat, p.lng) == ("Paris", 1, 48.85, None)  # 0 means "not set"
    assert client.post("/api/places", json={"name": "le bistrot"}).status_code == 409
    assert client.post("/api/places", json={"name": "X", "michelin_stars": 4}).status_code == 422
    assert client.post("/api/places", json={"name": "X", "lat": 120}).status_code == 422

    assert client.put(f"/api/places/{pid}", json={"name": "Le Bistrot", "michelin_stars": None}).status_code == 200
    _, p = get(Place, pid)
    assert (p.city, p.michelin_stars) == (None, None)

    r = client.delete(f"/api/places/{IDS['home']}")
    assert r.status_code == 409 and "visit" in detail(r)
    assert client.delete(f"/api/places/{IDS['unused']}").json() == {"deleted": IDS["unused"]}


def test_a_friends_home_by_at(client):
    """"@Mia": a Friend's Place named Mia, from the place form and from a tasting's or visit's new place."""
    r = client.post("/api/places", json={"name": "@Mia", "city": "Singapore", "type": "Restaurant"})
    _, p = get(Place, r.json()["id"])
    assert (p.name, p.type, p.city) == ("Mia", "Friend's Place", "Singapore")
    r = client.post("/api/visits", json={"date": "2025-07-02", "place": {"name": "@ Leo & Jen", "city": "Paris"}})
    assert r.status_code == 201
    _, p = get(Place, client.get(f"/api/forms/visits/{r.json()['id']}").json()["place"]["id"])
    assert (p.name, p.type) == ("Leo & Jen", "Friend's Place")


def test_visit_create_update_delete(client):
    r = client.post("/api/visits", json={"date": "2025-07-01", "place": IDS["home"], "notes": "Lunch"})
    assert r.status_code == 201 and r.json()["place_id"] == IDS["home"]
    vid = r.json()["id"]

    r = client.post("/api/visits", json={"date": "2025-07-02", "place": {"name": "Zén", "city": "Singapore", "type": "Restaurant"}})
    _, v = get(RestaurantVisit, r.json()["id"])
    assert (v.place.name, v.place.city) == ("Zén", "Singapore")

    assert client.post("/api/visits", json={"date": "2025-07-02"}).status_code == 422
    assert client.post("/api/visits", json={"date": "2025-07-02", "place": {"name": " "}}).status_code == 422

    assert client.put(f"/api/visits/{vid}", json={"date": "2025-07-03", "place": IDS["home"], "notes": ""}).status_code == 200
    form = client.get(f"/api/forms/visits/{vid}").json()
    assert (form["date"], form["notes"], form["place"]["id"]) == ("2025-07-03", None, IDS["home"])
    assert client.delete(f"/api/visits/{vid}").json() == {"deleted": vid, "place_id": IDS["home"]}


# --- Lookups and prefill ----------------------------------------------------------------------

def test_lookup_wines_by_producer_appellation_vintage(client):
    names = lambda r: [(w["producer"], w["cuvee"], w["vintage"]) for w in r.json()]
    assert ("Chateau de Coulaine", "Les Picasses", "2020") in names(client.get("/api/lookups/wines?q=coulaine picasses"))
    hits = client.get("/api/lookups/wines?q=cote rotie").json()  # accents and dashes ignored
    assert hits and all(w["appellation"] == "Côte-Rôtie" for w in hits)
    assert all(w["vintage"] == "2020" for w in client.get("/api/lookups/wines?q=chinon 2020").json())
    assert client.get("/api/lookups/wines?q=").json() == []
    stock = {w["id"]: w["stock"] for w in client.get(f"/api/lookups/wines?producer_id={IDS['coulaine']}").json()}
    assert stock[IDS["red"]] > 0


def test_lookup_bottles_only_in_stock(client):
    ids = {b["id"] for b in client.get("/api/lookups/bottles").json()}
    assert IDS["stocked"] in ids and IDS["gone"] not in ids
    b = client.get(f"/api/lookups/bottles?wine_id={IDS['red']}&q=H2").json()[0]
    assert b["label"] == "Chateau de Coulaine - Les Picasses (2020) - 75cl @ H2"


def test_other_lookups(client):
    assert client.get("/api/lookups/producers?q=coul").json()[0]["name"] == "Chateau de Coulaine"
    apps = client.get(f"/api/lookups/appellations?region_id={IDS['rhone']}").json()
    assert apps[0]["region"] == "Rhône"
    assert client.get("/api/lookups/vineyards?q=picasses").json()[0]["name"] == "Touraine - Chinon - Les Picasses"
    assert client.get("/api/lookups/places?q=singapore").json()[0]["name"] == "@Home"
    assert client.get("/api/lookups/varietals?q=franc").json()[0] == {"id": IDS["cf"], "name": "Cabernet Franc", "alias": None}
    assert client.get("/api/lookups/varietals?q=breton").json()[0] == {"id": IDS["cf"], "name": "Cabernet Franc", "alias": "Breton"}
    opts = client.get("/api/lookups/options").json()
    assert opts["currencies"] == ["SGD", "EUR", "USD", "GBP", "AUD"] and "75cl" in opts["bottle_sizes"]
    assert "Home" in opts["place_types"] and {"H2", "Home", "Wine bank"} <= set(opts["locations"])


def test_prefill(client):
    w = client.get(f"/api/forms/wines/{IDS['red']}").json()
    assert w["producer"]["name"] == "Chateau de Coulaine" and w["vineyard"]["name"] == "Touraine - Chinon - Les Picasses"
    b = client.get(f"/api/forms/bottles/{IDS['stocked']}").json()
    assert b["wine"]["id"] == IDS["red"] and b["option"]["location"] == "H2"
    for kind in ("producers", "wines", "bottles", "tastings", "places", "visits"):
        assert client.get(f"/api/forms/{kind}/9999").status_code == 404


def test_next_sequence_follows_the_evening(client):
    with_place = client.post("/api/places", json={"name": "Sequence Bistro"}).json()["id"]
    day = "2025-03-01"
    url = "/api/lookups/next-sequence"
    assert client.get(url, params={"date": day, "place_id": with_place}).json() == {"next": 1, "count": 0}

    bottle = client.get("/api/lookups/bottles", params={"q": ""}).json()[0]["id"]
    note = {"source": "cellar", "bottle_id": bottle, "consume": False, "date": day, "place": with_place}
    client.post("/api/tastings", json={**note, "sequence": 1})
    client.post("/api/tastings", json={**note, "sequence": None})  # unnumbered notes still take a slot
    assert client.get(url, params={"date": day, "place_id": with_place}).json() == {"next": 3, "count": 2}

    client.post("/api/tastings", json={**note, "sequence": 5})
    assert client.get(url, params={"date": day, "place_id": with_place}).json()["next"] == 6
    assert client.get(url, params={"date": "2025-03-02", "place_id": with_place}).json()["next"] == 1


def test_lookups_find_aliases(client):
    from db import Appellation, Producer
    s, a = get(Appellation, IDS["chinon"])
    a.aliases = "Kinon"
    p = s.get(Producer, IDS["coulaine"])
    p.aliases = "Coulaine"
    s.commit()
    s.close()
    assert [x["id"] for x in client.get("/api/lookups/appellations", params={"q": "kinon"}).json()] == [IDS["chinon"]]
    assert IDS["coulaine"] in [x["id"] for x in client.get("/api/lookups/producers", params={"q": "coulaine"}).json()]


def test_critic_scores(client):
    wid = client.post("/api/wines", json={"producer": IDS["coulaine"], "cuvee": "Scores", "vintage": "2019",
                                          "type": "Red"}).json()["id"]
    client.post(f"/api/wines/{wid}/scores", json={"critic": "Robert Parker", "score": "93"})
    r = client.post(f"/api/wines/{wid}/scores", json={"critic": "Vinous", "score": "94", "note": "Silky.",
                                                      "url": "https://vinous.com/x", "date": "2024-05-01"})
    assert r.status_code == 200
    client.post(f"/api/wines/{wid}/scores", json={"critic": "vinous", "score": "95"})  # the same critic: replaced
    client.post(f"/api/wines/{wid}/scores", json={"critic": "Jancis Robinson", "score": "17"})
    w = client.get(f"/api/wines/{wid}").json()
    # The preferred critic (Robert Parker by default) first, then by name
    assert [(s["critic"], s["score"], s["note"]) for s in w["scores"]] == [
        ("Robert Parker", "93", None), ("Jancis Robinson", "17", None), ("Vinous", "95", None)]
    assert "Vinous" in client.get("/api/lookups/critics").json()
    assert client.delete(f"/api/wines/{wid}/scores", params={"critic": "Vinous"}).status_code == 200
    assert [s["critic"] for s in client.get(f"/api/wines/{wid}").json()["scores"]] == ["Robert Parker", "Jancis Robinson"]
    assert client.delete(f"/api/wines/{wid}/scores", params={"critic": "Vinous"}).status_code == 404


def test_wine_grapes_and_blend_style(client):
    """A wine's grapes in order (the first its main grape), its blend style (an older text read)."""
    r = client.post("/api/wines", json={
        "producer": {"name": "Château Grapes"}, "cuvee": "Assemblage", "vintage": "2019", "type": "Red",
        "grapes": [{"varietal": {"name": "Merlot"}, "share": 70}, {"varietal": IDS["cf"], "share": 30}],
        "blend": "Bordeaux Blend"})
    assert r.status_code == 201, r.text
    wid = r.json()["id"]
    form = client.get(f"/api/forms/wines/{wid}").json()
    assert [(g["varietal"]["name"], g["share"]) for g in form["grapes"]] == [("Merlot", 70), ("Cabernet Franc", 30)]
    assert form["blend"] == "Bordeaux blend"
    page = client.get(f"/api/wines/{wid}").json()
    assert page["varietal"] == "Merlot" and [g["name"] for g in page["grapes"]] == ["Merlot", "Cabernet Franc"]
    # the grape page counts the wines a grape is in, not only those it leads
    assert "Château Grapes" in [p["name"] for p in client.get(f"/api/grapes/{IDS['cf']}").json()["producers"]]
    # an older client sending only the main grape: it replaces the first, the second stays
    client.put(f"/api/wines/{wid}", json={"producer": {"name": "Château Grapes"}, "cuvee": "Assemblage",
                                          "vintage": "2019", "type": "Red", "varietal": {"name": "Malbec"}})
    form = client.get(f"/api/forms/wines/{wid}").json()
    assert [g["varietal"]["name"] for g in form["grapes"]] == ["Malbec", "Cabernet Franc"]
    assert form["blend"] is None
    assert {"Bordeaux blend", "Field blend"} <= set(client.get("/api/lookups/options").json()["blend_styles"])
