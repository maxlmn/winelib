"""Settings › Maintenance › Import a cellar: CellarTracker's and Vivino's exports (as documented), columns recognised,
a preview by producer to tick, a run adding wines, bottles and tastings; nothing added twice."""
import time
from datetime import date

import jobs
from db import Appellation, Bottle, Producer, Region, TastingNote, Varietal, Wine

# CellarTracker's cellar export: month/day/year dates, a Designation besides the whole name, Color and Category
CT = """iWine,Type,Color,Category,Size,Currency,Price,Vintage,Wine,Locale,Country,Region,SubRegion,Appellation,Producer,SortProducer,Varietal,MasterVarietal,Designation,Vineyard,Location,Bin,Quantity,PurchaseDate,Store
11,Red,Red,Dry,750ml,EUR,120,2016,Clos Rougeard Saumur-Champigny Le Bourg,"France, Loire Valley",France,Loire Valley,Anjou-Saumur,Saumur-Champigny,Clos Rougeard,Rougeard,Cabernet Franc,Cabernet Franc,Le Bourg,Unknown,H1,,2,3/1/2024,Caviste
11,Red,Red,Dry,750ml,EUR,130,2016,Clos Rougeard Saumur-Champigny Le Bourg,"France, Loire Valley",France,Loire Valley,Anjou-Saumur,Saumur-Champigny,Clos Rougeard,Rougeard,Cabernet Franc,Cabernet Franc,Le Bourg,Unknown,H2,,1,10/25/2025,Caviste
12,Red,Red,Dry,1500ml,EUR,85.50,2018,Clos Rougeard Saumur-Champigny Les Poyeux,"France, Loire Valley",France,Loire Valley,Anjou-Saumur,Saumur-Champigny,Clos Rougeard,Rougeard,Cabernet Franc,Cabernet Franc,Les Poyeux,Unknown,Cave,A3,3,1/15/2024,
13,White,White,Sweet,750ml,EUR,45,2020,Domaine Huet Vouvray Le Haut-Lieu Moelleux,"France, Loire Valley",France,Loire Valley,Touraine,Vouvray,Domaine Huet,Huet,Chenin Blanc,Chenin Blanc,Le Haut-Lieu Moelleux,Unknown,H3,,6,2/2/2024,
14,White,Rosé,Sparkling,750ml,,,NV,Champagne Delorme Rosé de Saignée,"France, Champagne",France,Champagne,,Champagne,Champagne Delorme,Delorme,Pinot Noir,Pinot Noir,Rosé de Saignée,,,,,,
"""
# Vivino's full_wine_list.csv: ratings out of 5, a scan date with its time
VIVINO = """Winery,Wine name,Vintage,Region,Country,Regional wine style,Average rating,Scan date,Scan/Review Location,Your rating,Your review,Personal Note,Wine type,Drinking Window,Link to wine,Label image
Clos Rougeard,Le Bourg,2016,Saumur-Champigny,France,Loire Cabernet Franc,4.4,2025-01-02 20:15:00,,4.5,Superb.,,Red wine,,https://www.vivino.com/w/1,
Clos Rougeard,Le Bourg,2016,Saumur-Champigny,France,Loire Cabernet Franc,4.4,2025-01-02 20:15:00,,4.5,Superb.,,Red wine,,https://www.vivino.com/w/1,
"""


def seed(s):
    loire = Region(name="Loire", country="France")
    sc = Appellation(name="Saumur-Champigny", region_obj=loire)
    bourg = Wine(producer=Producer(name="Clos Rougeard", region_obj=loire), cuvee="Le Bourg", vintage="2016",
                 type="Red", appellation=sc, region_obj=loire)
    s.add_all([Bottle(wine=bourg, qty=2, location="H1", price=120, currency="EUR", purchase_date=date(2024, 3, 1)),
               Region(name="Champagne", country="France"), Appellation(name="Champagne", region_id=None),
               Varietal(name="Cabernet Franc")])


def wait(client):
    for _ in range(300):
        job = client.get("/api/maintenance/job").json()
        if job and job["status"] != "running":
            return job
        time.sleep(0.02)
    raise AssertionError("job didn't finish")


def run(client, text, **body):
    assert client.post("/api/maintenance/cellar_csv", json={"text": text, **body}).status_code == 202
    return wait(client)


def test_cellartracker(client):
    job = run(client, CT)
    assert job["status"] == "done", job["log"]
    r = job["result"]
    m = r["columns"]["mapping"]
    assert (m["producer"], m["cuvee"], m["colour"], m["category"], m["grape"]) == (
        "Producer", "Designation", "Color", "Category", "Varietal")
    items = {i["pick"]["key"]: i for i in r["items"]}
    assert set(items) == {"3", "4", "5", "6"}  # line 2: your bottles, already there
    assert "1 bottle at H2" in items["3"]["detail"] and items["3"]["pick"]["flag"]  # your wine
    assert "new wine" in items["4"]["detail"] and "3 bottles at Cave A3" in items["4"]["detail"]
    assert "new producer" in items["5"]["detail"] and "Sweet" in items["5"]["detail"] and "new grape Chenin Blanc" in items["5"]["detail"]
    assert "Bubbles Rose" in items["6"]["detail"]
    assert "already there: 1" in r["summary"] and "Vouvray (1)" in r["summary"]  # not in the reference list

    job = run(client, CT, commit=True, keys=["3", "4", "5", "6"])
    assert job["result"]["summary"] == "Added 2 producers, 3 wines, 3 bottles, 2 grapes.", job["result"]  # Chenin, Pinot Noir
    poyeux = client.get("/api/lookups/wines", params={"producer_id": 1, "q": "Poyeux"}).json()[0]
    assert (poyeux["vintage"], poyeux["appellation"], poyeux["varietal"]) == ("2018", "Saumur-Champigny", "Cabernet Franc")
    cellar = {(b["cuvee"], b["location"]): b for b in client.get("/api/cellar").json()["bottles"]}
    p = cellar[("Les Poyeux", "Cave A3")]
    assert (p["qty"], p["format"], p["price"], p["purchase_date"]) == (3, "150cl", 85.5, "2024-01-15")  # month first
    assert cellar[("Le Bourg", "H2")]["purchase_date"] == "2025-10-25"
    assert run(client, CT)["result"]["items"] == []  # imported twice: nothing new


def test_vivino(client):
    job = run(client, VIVINO)
    r = job["result"]
    assert r["columns"]["mapping"]["rating"] == "Your rating" and r["columns"]["mapping"]["tasting_date"] == "Scan date"
    (item,) = r["items"]  # the second row is the same tasting
    assert "tasting 02 Jan 2025 (90)" in item["detail"]  # 4.5 stars -> 90
    run(client, VIVINO, commit=True, keys=[item["pick"]["key"]])
    from main import app
    from db import get_session
    s = next(app.dependency_overrides[get_session]())
    (t,) = s.query(TastingNote).all()
    assert (t.date, t.rating, t.notes, t.bottle.qty, t.bottle.location) == (date(2025, 1, 2), 90, "Superb.", 0, "Consumed")
    s.close()


def test_needs_a_file(client):
    assert client.post("/api/maintenance/cellar_csv", json={}).status_code == 422
    job = run(client, "Who;What\nX;Y\n")
    assert job["result"]["items"] == [] and "pick the column for producer" in job["result"]["summary"]


BLENDS = """Producer,Wine,Vintage,Color,Varietal,Quantity,Location
Château Musar,Rouge,2017,Red,Red Bordeaux Blend,1,H4
Domaine Gramenon,La Sagesse,2021,Red,"Grenache 80%, Cabernet Franc 20%",2,H5
"""


def test_blends_and_grape_lists(client):
    """CellarTracker's style in its Varietal column becomes the wine's blend; a list, its grapes (shares kept)."""
    job = run(client, BLENDS)
    items = {i["pick"]["key"]: i for i in job["result"]["items"]}
    assert "Bordeaux blend" in items["2"]["detail"] and "new grape" not in items["2"]["detail"]
    assert "Grenache 80%, Cabernet Franc 20%" in items["3"]["detail"] and "new grape Grenache" in items["3"]["detail"]
    run(client, BLENDS, commit=True, keys=["2", "3"])
    from main import app
    from db import get_session
    s = next(app.dependency_overrides[get_session]())
    musar = s.query(Wine).filter_by(cuvee="Rouge").one()
    sagesse = s.query(Wine).filter_by(cuvee="La Sagesse").one()
    assert (musar.blend, musar.grapes, musar.varietal_id) == ("Bordeaux blend", [], None)
    assert [(g.varietal.name, g.share) for g in sagesse.grapes] == [("Grenache", 80), ("Cabernet Franc", 20)]
    assert sagesse.varietal.name == "Grenache"
    s.close()


def test_grapes_of():
    from tasks.import_cellar import grapes_of
    assert grapes_of("White Rhone Blend") == ("Rhône blend", [])
    assert grapes_of("GSM") == ("Rhône blend", [])
    assert grapes_of("Syrah / Viognier (5%)") == (None, [("Syrah", None), ("Viognier", 5)])
    assert grapes_of("Mueller-Thurgau") == (None, [("Mueller-Thurgau", None)])
    assert grapes_of("Pinot Noir and Chardonnay") == (None, [("Pinot Noir", None), ("Chardonnay", None)])
    assert grapes_of("") == (None, [])
