"""Settings › Maintenance › Import critic scores: a CSV with a critic named, its columns recognised, a preview to
tick, a run saving the ticked rows."""
import time

import jobs
from db import Appellation, CriticScore, Producer, Region, Varietal, Wine

CSV = """Domaine;Cuvée;Millésime;Couleur;Cépage;Appellation;Points;Tasting note;URL;Date
Clos Rougeard;Le Bourg;2019;Rouge;;Saumur Champigny;96;Dense.;https://v/1;2024-03-01
Clos Rougeard;Le Bourg;2018;;;;95;Fine.;;
Clos Rougeard;Les Poyeux;2019;;;Saumur-Champigny;94;;;
Clos Rougeard;;2019;Blanc;Chenin Blanc;Saumur;93;;;
Clos Rougeard;Le Bourg;2019;;;;97;Again.;;
Rougeard Clos;Brézé;2020;White;;;92;;;
E. Guigal;La Mouline;2020;;;;99;;;
Clos Rougeard;Le Bourg;2017;;;Ermitage;95;;;
Clos Rougeard;Le Bourg;n.v.;;;;90;;;
Clos Rougeard;Le Bourg;20x9;;;;90;;;
"""


def seed(s):
    loire = Region(name="Loire", country="France")
    sc = Appellation(name="Saumur-Champigny", region_obj=loire, aliases="Saumur Champigny")
    saumur = Appellation(name="Saumur", region_obj=loire)
    rougeard = Producer(name="Clos Rougeard", region_obj=loire)
    bourg = Wine(producer=rougeard, cuvee="Le Bourg", vintage="2019", type="Red", appellation=sc)
    bourg18 = Wine(producer=rougeard, cuvee="Le Bourg", vintage="2018", type="Red", appellation=sc)
    bourg18.scores.append(CriticScore(critic="Vinous", score="95", note="Fine."))
    poyeux = Wine(producer=rougeard, cuvee="Les Poyeux", vintage="2019", type="Red", appellation=sc)
    poyeux.scores.append(CriticScore(critic="Vinous", score="92"))
    s.add_all([bourg, bourg18, poyeux, saumur, Varietal(name="Chenin Blanc")])


from conftest import wait_job as wait  # noqa: E402


def run(client, **body):
    r = client.post("/api/maintenance/scores_csv", json={"text": CSV, "critic": " Vinous ", **body})
    assert r.status_code == 202, r.json()
    assert "_text" not in r.json()["params"]  # the file stays out of the job's public view
    return wait(client)


def test_needs_a_file_and_a_critic(client):
    assert client.post("/api/maintenance/scores_csv", json={"critic": "Vinous"}).status_code == 422
    assert client.post("/api/maintenance/scores_csv", json={"text": CSV, "critic": " "}).status_code == 422
    assert client.post("/api/maintenance/scores_csv", json={"text": CSV, "critic": "Vinous", "commit": True}).status_code == 422


def test_preview_then_import(client):
    job = run(client)
    assert job["status"] == "done", job["log"]
    r = job["result"]
    assert r["columns"]["mapping"] == {"producer": "Domaine", "cuvee": "Cuvée", "vintage": "Millésime", "colour": "Couleur",
                                       "grape": "Cépage", "appellation": "Appellation", "score": "Points",
                                       "note": "Tasting note", "link": "URL", "date": "Date"}
    items = {i["pick"]["key"]: i for i in r["items"]}
    # 2: yours, no Vinous score; 3: a different Vinous score (unticked); 4: a new white; 7: by its distinctive words
    assert set(items) == {"2", "4", "5", "7", "10"}  # 10: n.v., a new NV
    assert items["2"]["label"] == "Le Bourg 2019" and items["2"]["href"] == "https://v/1"
    assert (items["2"]["pick"]["on"], items["2"]["pick"]["flag"]) == (True, True)
    assert items["4"]["pick"]["on"] is False and "Vinous 92 now" in items["4"]["detail"]
    assert items["5"]["label"] == "(plain) 2019" and "new wine" in items["5"]["detail"] and items["5"]["pick"]["on"]
    assert items["7"]["pick"]["on"] is False and "check: producer" in items["7"]["detail"]
    summary = r["summary"]
    assert "already there (same score): 1" in summary  # the 2018: same score and note
    assert "twice in the file: 1" in summary  # line 6, the 2019 Le Bourg again
    assert "Not recognised: Ermitage (1)" in summary and "vintage not understood: 1" in summary
    assert r["unknown"] == [{"alias": "E. Guigal", "reviews": 1, "examples": ["La Mouline 2020"], "fits": []}]

    job = run(client, commit=True, keys=["2", "5"])
    assert job["result"]["summary"] == "Vinous: 1 wine added, 1 score given to wines you have, 0 replaced."
    wine = client.get("/api/wines/1").json()
    assert [(s["critic"], s["score"], s["note"], s["url"], s["date"]) for s in wine["scores"]] == [
        ("Vinous", "96", "Dense.", "https://v/1", "2024-03-01")]
    new = client.get("/api/wines/4").json()
    assert (new["cuvee"], new["vintage"], new["color"], new["appellation"]["name"], new["varietal"]) == (
        "", "2019", "White", "Saumur", "Chenin Blanc")
    left = {i["pick"]["key"] for i in run(client)["result"]["items"]}
    assert left == {"4", "7", "10"}  # line 2 has its score now, line 5's wine exists with it


def test_columns_picked_by_hand(client):
    text = "Who;What;When;Pts\nClos Rougeard;Le Bourg;2019;98\n"  # (it has Vinous 96 from the test above)
    r = client.post("/api/maintenance/scores_csv", json={"text": text, "critic": "Vinous"})
    job = wait(client)
    assert job["result"]["items"] == [] and "pick the column for producer, vintage" in job["result"]["summary"]
    assert job["result"]["columns"]["headers"] == ["Who", "What", "When", "Pts"]
    r = client.post("/api/maintenance/scores_csv", json={"text": text, "critic": "Vinous", "mapping": {
        "producer": "Who", "cuvee": "What", "vintage": "When", "score": "Pts"}})
    assert r.status_code == 202
    job = wait(client)
    assert [i["pick"]["key"] for i in job["result"]["items"]] == ["2"]
