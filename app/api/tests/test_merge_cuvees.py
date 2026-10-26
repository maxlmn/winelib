"""Merging two spellings of a cuvée (winelib_utils/merge_cuvees.py), from the similar cuvée names report."""
import time

import pytest

import jobs
from db import Bottle, CriticScore, Producer, TastingNote, Wine
from conftest import rp, rp_of


def seed(s):
    p = Producer(name="Clos Rougeard")
    kept = Wine(producer=p, cuvee="Les Poyeux", vintage="2016", type="Red")
    twin = Wine(producer=p, cuvee="Poyeux", vintage="2016", type="Red", scores=rp("95", note="Dense."), lwin="1234567")
    alone = Wine(producer=p, cuvee="Poyeux", vintage="2017", type="Red")  # no "Les Poyeux" 2017
    white = Wine(producer=p, cuvee="Poyeux", vintage="2016", type="White")  # the red 2016's name, but white
    other = Producer(name="Domaine Huet")
    kept.scores += [CriticScore(critic="Vinous", score="-"), CriticScore(critic="Jancis Robinson", score="17")]
    twin.scores += [CriticScore(critic="Vinous", score="94", note="Firm."), CriticScore(critic="Jancis Robinson", score="16")]
    s.add_all([kept, twin, alone, white,
               Wine(producer=other, cuvee="Le Mont", vintage="2019", type="White"),
               Wine(producer=other, cuvee="Mont", vintage="2019", type="Red")])  # similar names, not one cuvée
    s.flush()
    line = Bottle(wine=twin, qty=1, location="H3")
    s.add_all([Bottle(wine=kept, qty=2, location="H1"), line, Bottle(wine=alone, qty=1, location="H4")])
    s.flush()
    s.add(TastingNote(bottle=line, rating=95, notes="Superb"))


def wait(client):
    for _ in range(200):
        job = client.get("/api/maintenance/job").json()
        if job and job["status"] != "running":
            return job
        time.sleep(0.02)
    raise AssertionError("job didn't finish")


@pytest.fixture(autouse=True)
def no_job_left():
    yield
    job = jobs.current()
    if job is not None and job.status == "running":
        job.thread.join(5)


PAIR = {"producer_id": 1, "keep": "Les Poyeux", "drop": "Poyeux"}


def test_report_offers_the_pair(client):
    client.post("/api/maintenance/similar", json={})
    (item,) = wait(client)["result"]["items"]
    assert item["merge"] == {"task": "merge_cuvees", "a": "Les Poyeux", "b": "Poyeux", "wines": [1, 3],
                             "pick": {"a": PAIR, "b": {**PAIR, "keep": "Poyeux", "drop": "Les Poyeux"}}}  # Huet's red/white pair isn't one


def test_red_and_white_are_not_duplicates(client):
    client.post("/api/maintenance/duplicates", json={})
    assert wait(client)["result"]["summary"].startswith("0 groups")  # Poyeux 2016 red and white


def test_preview_changes_nothing(client):
    client.post("/api/maintenance/merge_cuvees", json={"pairs": [PAIR]})
    job = wait(client)
    assert job["status"] == "done" and not job["commit"]
    assert "2 wines would be renamed, 1 wine would be merged" in job["result"]["summary"]  # the white has no twin
    assert client.get("/api/wines/2").status_code == 200 and client.get("/api/wines/3").json()["cuvee"] == "Poyeux"


def test_merge_moves_lines_keeps_notes_and_leaves_no_orphans(client):
    client.post("/api/maintenance/merge_cuvees", json={"pairs": [PAIR], "commit": True})
    job = wait(client)
    assert job["status"] == "done", job["log"]
    kept = client.get("/api/wines/1").json()
    # The page lists every vintage of the cuvée: the renamed 2017 is one of them now
    assert sorted(b["qty"] for b in kept["cellar"] if b["wine_id"] == 1) == [1, 2]  # the twin's line moved over
    assert [t["notes"] for t in kept["tastings"] if t["wine_id"] == 1] == ["Superb"]  # its tasting note followed
    assert rp_of(kept) == "95" and kept["lwin"] == "1234567"  # what the kept wine lacked
    # every critic's: Vinous (it had none, "-"), not Jancis Robinson (it had its own)
    assert {s["critic"]: (s["score"], s["note"]) for s in kept["scores"]} == {
        "Robert Parker": ("95", "Dense."), "Vinous": ("94", "Firm."), "Jancis Robinson": ("17", None)}
    assert client.get("/api/wines/2").status_code == 404  # emptied, deleted
    assert client.get("/api/wines/3").json()["cuvee"] == "Les Poyeux"  # no twin: renamed
    white = client.get("/api/wines/4").json()  # the red's twin wasn't the white's
    assert (white["cuvee"], white["color"]) == ("Les Poyeux", "White")
    client.post("/api/maintenance/orphans", json={})
    assert wait(client)["result"]["summary"].startswith("0 notes without a bottle, 0 bottles without a wine")


def test_a_merge_that_would_orphan_is_undone(client, monkeypatch):
    from winelib_utils import merge_cuvees
    real = merge_cuvees.find_orphans
    calls = []

    def worse(session):  # pretend the merge orphaned a note
        r = real(session)
        calls.append(1)
        return r if len(calls) == 1 else {**r, "notes": r["notes"] + [(1, 1, "x")]}
    monkeypatch.setattr(merge_cuvees, "find_orphans", worse)
    client.post("/api/maintenance/merge_cuvees", json={"pairs": [{"producer_id": 1, "keep": "Les Poyeux", "drop": "Poyeux"}],
                                                        "commit": True})
    job = wait(client)
    assert job["status"] == "failed" and "orphan" in job["log"][-1]


def test_needs_pairs(client):
    assert client.post("/api/maintenance/merge_cuvees", json={"commit": True}).status_code == 422
    assert "merge_cuvees" not in {t["id"] for t in client.get("/api/maintenance").json()["tasks"]}
