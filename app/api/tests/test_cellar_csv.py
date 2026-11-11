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


from conftest import wait_job as wait  # noqa: E402


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
    assert job["result"]["summary"] == "Added 2 producers, 3 wines, 10 bottles, 2 grapes.", job["result"]  # Chenin, Pinot Noir
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


def test_a_plain_wine_named_after_its_appellation_is_yours(client):
    """"Jamet, Côte-Rôtie": the producer's plain wine (no cuvée), already in the cellar, not a new wine named after
    its appellation; and in a whole name ("Wine") a hyphenated appellation is cut off too."""
    import db
    session = next(client.app.dependency_overrides[db.get_session]())
    rhone = Region(name="Rhone", country="France")
    cr = Appellation(name="Côte-Rôtie", region_obj=rhone)
    session.add(Wine(producer=Producer(name="Domaine Jamet", region_obj=rhone), cuvee="", vintage="2019",
                     appellation=cr, region_obj=rhone))
    session.commit()
    for csv in ("Producer,Cuvee,Vintage,Appellation,Quantity\nJamet,Côte-Rôtie,2019,Côte-Rôtie,2\n",
                "Producer,Wine,Vintage,Appellation,Quantity\nDomaine Jamet,Domaine Jamet Côte-Rôtie,2019,Côte-Rôtie,2\n",
                "Producer,Wine,Vintage,Appellation,Quantity\nDomaine Jamet,Côte-Rôtie Côte Brune,2019,Côte-Rôtie,1\n"):
        (item,) = run(client, csv)["result"]["items"]
        assert "new wine" not in item["detail"] or "Côte Brune" in csv, (csv, item)
        if "Côte Brune" in csv:
            assert item["label"].startswith("Côte Brune"), item["label"]  # the appellation cut off its whole name
        else:
            assert item["pick"]["flag"], item  # your wine


def session_of(client):
    import db
    return next(client.app.dependency_overrides[db.get_session]())


def test_identical_rows_add_up(client):
    """Two identical bottle rows are two bottles; against the cellar, a line is already there only with the same
    location, size, purchase date and price, and as many bottles (those drunk since counted)."""
    s = session_of(client)
    wine = Wine(producer=Producer(name="Domaine Dupont"), cuvee="Les Vignes", vintage="2019", type="Red")
    drunk = Bottle(wine=wine, qty=0, location="Cave", price=30, currency="EUR")
    s.add_all([drunk, TastingNote(bottle=drunk, date=date(2024, 5, 1), rating=90),
               Bottle(wine=wine, qty=1, location="Cave", price=None, currency="EUR")])
    s.commit()
    s.close()
    text = ("Producer,Wine,Vintage,Colour,Quantity,Location,Price\n"
            "Domaine X,Cuvee A,2019,Red,1,Cave,20\n"
            "Domaine X,Cuvee A,2019,Red,1,Cave,20\n"
            "Domaine Dupont,Les Vignes,2019,Red,2,Cave,30\n"  # one of the two drunk already
            "Domaine Dupont,Les Vignes,2019,Red,1,Cave,25\n")  # not your price-less line
    items = {i["pick"]["key"]: i for i in run(client, text)["result"]["items"]}
    assert set(items) == {"2", "3", "4", "5"}
    assert "1 bottle at Cave" in items["2"]["detail"] and "1 bottle at Cave" in items["3"]["detail"]
    assert "1 bottle at Cave (1 already there)" in items["4"]["detail"]
    assert "1 bottle at Cave" in items["5"]["detail"]
    run(client, text, commit=True, keys=list(items))
    s = session_of(client)
    x = s.query(Wine).filter_by(cuvee="Cuvee A").one()
    assert sum(b.qty for b in x.inventory) == 2
    s.close()
    assert run(client, text)["result"]["items"] == []  # imported twice: nothing new


def test_tastings_with_only_a_note(client):
    text = ('Producer,Wine,Vintage,Tasting notes\nDomaine Y,Cuvee B,2019,"Lovely, first bottle"\n'
            'Domaine Y,Cuvee B,2019,"Tired, second bottle"\nDomaine Y,Cuvee B,2019,"Tired,  second bottle"\n')
    items = run(client, text)["result"]["items"]
    assert [i["pick"]["key"] for i in items] == ["2", "3"]  # line 4: the same note again
    run(client, text, commit=True, keys=["2", "3"])
    s = session_of(client)
    assert sorted(t.notes for t in s.query(TastingNote).all()) == ["Lovely, first bottle", "Tired, second bottle"]
    s.close()
    assert run(client, text)["result"]["items"] == []


def test_a_close_cuvee_is_to_check(client):
    """"Cabernet Sauvignon Napa Valley Reserve" isn't your "Cabernet Sauvignon Napa Valley": offered, unticked."""
    s = session_of(client)
    s.add_all([Wine(producer=Producer(name="Robert Mondavi"), cuvee="Cabernet Sauvignon Napa Valley", vintage="2018",
                    type="Red"),
               Wine(producer=Producer(name="Domaine Fourrier"), cuvee="Gevrey-Chambertin 1er Cru Clos Saint-Jacques",
                    vintage="2019", type="Red")])
    s.commit()
    s.close()
    text = ("Producer,Cuvee,Vintage,Quantity\nRobert Mondavi,Cabernet Sauvignon Napa Valley Reserve,2018,3\n"
            "Robert Mondavi,Cabernet Sauvignon Napa Valley,2018,1\n"
            "Domaine Fourrier,Gevrey-Chambertin 1er Cru Lavaux Saint-Jacques,2019,1\n")
    items = {i["pick"]["key"]: i for i in run(client, text)["result"]["items"]}
    assert items["2"]["pick"]["on"] is False
    assert "check: close to your Cabernet Sauvignon Napa Valley 2018" in items["2"]["detail"]
    assert items["3"]["pick"]["on"] is True and "close to" not in items["3"]["detail"]
    assert items["4"]["pick"]["on"] is False and "close to your Gevrey" in items["4"]["detail"]


def test_numbers():
    from tasks.import_cellar import decimal_comma, number, rating_of
    assert number("1.250,00") == 1250 and number("1,500.50") == 1500.5 and number("12,50") == 12.5
    assert number("1.5") == 1.5 and number("1.500") == 1.5 and number("€45") == 45 and number("1,500") == 1500
    comma = decimal_comma(["1.500", "12,50", ""])
    assert comma is True and number("1.500", comma) == 1500 and number("1,5", comma) == 1.5
    assert decimal_comma(["12.50", "1,250.00"]) is False and decimal_comma(["20", "1.500"]) is None
    assert rating_of("93-95") == 94 and rating_of("93/95") == 94 and rating_of("16/20") == 16
    assert rating_of("4,5") == 4.5 and rating_of("9395") is None and rating_of("") is None


def test_prices_and_rating_ranges(client):
    """A decimal-comma price column ("1.500" is 1500), and a rating range doesn't change the file's scale."""
    text = ("Producer;Wine;Vintage;Quantity;Location;Price;Rating;Tasting date\n"
            "Domaine Z;A;2019;1;Cave;1.500;93-95;2024-01-02\nDomaine Z;B;2019;1;Cave;12,50;90;2024-01-03\n")
    items = {i["pick"]["key"]: i for i in run(client, text)["result"]["items"]}
    assert "(94)" in items["2"]["detail"] and "(90)" in items["3"]["detail"]
    run(client, text, commit=True, keys=["2", "3"])
    s = session_of(client)
    assert sorted(b.price for b in s.query(Bottle).filter(Bottle.location == "Cave")) == [12.5, 1500]
    s.close()


def test_dates_order(client):
    """Dates every one of which reads both ways: day first (said in the summary, to pick otherwise), month first for
    CellarTracker's export."""
    text = "Producer,Wine,Vintage,Tasting date,Rating\nDomaine D,A,2019,3/4/2024,90\n"
    r = run(client, text)["result"]
    assert r["columns"]["dates"] == "dmy" and "Dates read as day/month: 3/4/2024 = 3 April 2024" in r["summary"]
    assert "the file doesn't say" in r["summary"] and "tasting 03 Apr 2024" in r["items"][0]["detail"]
    r = run(client, text, date_order="mdy")["result"]
    assert r["columns"]["dates"] == "mdy" and "tasting 04 Mar 2024" in r["items"][0]["detail"]
    run(client, text, commit=True, keys=["2"], date_order="mdy")
    s = session_of(client)
    assert s.query(TastingNote).one().date == date(2024, 3, 4)
    s.close()
    r = run(client, "iWine,Producer,Wine,Vintage,PurchaseDate,Quantity\n1,Domaine E,A,2019,3/4/2024,1\n")["result"]
    assert r["columns"]["dates"] == "mdy" and "= 4 March 2024" in r["summary"]
    r = run(client, "Producer,Wine,Vintage,Quantity\nDomaine E,A,2019,1\n")["result"]
    assert "dates" not in r["columns"] and "Dates read" not in r["summary"]


def test_line_numbers_are_the_spreadsheets(client):
    text = "Producer,Wine,Vintage,Quantity\nDomaine F,A,2019,1\n,,,\n\nDomaine F,B,2019,1\n"
    items = run(client, text)["result"]["items"]
    assert [i["pick"]["key"] for i in items] == ["2", "5"] and "line 5" in items[1]["detail"]


def test_vivino_price():
    from tasks.import_cellar import columns
    assert columns(["Winery", "Wine name", "Wine price"])["price"] == "Wine price"


def test_cellartracker_unknowns_and_non_vintage():
    """CellarTracker's "Unknown" isn't a name (a cuvée "Unknown"), its vineyard names the wine that has no
    designation, and its vintage 1001 is a non-vintage wine."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from db import Base
    from tasks import import_cellar as ic
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    rows = [{"Producer": "Domaine Jamet", "Designation": "Unknown", "Vineyard": "Unknown", "Vintage": "2019", "Quantity": "3"},
            {"Producer": "Ridge Vineyards", "Designation": "Unknown", "Vineyard": "Monte Bello", "Vintage": "2016", "Quantity": "6"},
            {"Producer": "Pierre Péters", "Designation": "Cuvée de Réserve", "Vineyard": "Unknown", "Vintage": "1001", "Quantity": "3"}]
    with Session(engine) as s:
        items = ic.plan(s, rows, ic.columns(list(rows[0])))
        assert [(it["cuvee"], it["vintage"]) for it in items] == [("", "2019"), ("Monte Bello", "2016"), ("Cuvée de Réserve", "NV")]
        assert ic.apply(s, items)["bottles"] == 12  # the bottles, not their 3 lines
