"""Vineyards for your wines (vineyard_names.py): a cuvée named after a vineyard of its region that has an outline is
linked to it, every vintage; the site's kind, the grape or a village's adjective around the name are allowed
("Escolle Vineyard", "Wehlener Sonnenuhr Spätlese"); a vineyard named only with common words isn't offered ("Blanc"
isn't "Les Blancs"); one in a village the appellation doesn't name is the user's to check."""
from conftest import wait_job
from db import Appellation, Producer, Region, Vineyard, Wine

import vineyard_names as vn


def seed(s):
    ca, mosel, rhone = Region(name="California"), Region(name="Mosel"), Region(name="Rhone")
    slh = Appellation(name="Santa Lucia Highlands", region_obj=ca)
    mo = Appellation(name="Mosel", region_obj=mosel)
    cornas, herm = Appellation(name="Cornas", region_obj=rhone), Appellation(name="Hermitage", region_obj=rhone)
    s.add_all([
        Vineyard(name="Escolle", village="Santa Lucia Highlands", region_obj=ca, boundary="vineyard:california:5068"),
        Vineyard(name="Wehlener Sonnenuhr", village="Wehlen", region_obj=mosel, boundary="vineyard:mosel:1"),
        Vineyard(name="Chaillot", village="Cornas", region_obj=rhone, boundary="vineyard:rhone:1"),
        Vineyard(name="Les Blancs", village="Crozes-Hermitage", region_obj=rhone, boundary="vineyard:rhone:2"),
        Vineyard(name="Sans Contour", village="Cornas", region_obj=rhone),  # no outline: not offered
    ])
    cara, prum, allemand, chave = (Producer(name=n) for n in ("Caraccioli Cellars", "J.J. Prüm", "Thierry Allemand", "Jean-Louis Chave"))
    s.add_all([
        Wine(producer=cara, cuvee="Escolle Vineyard", vintage="2018", type="Red", appellation=slh, region_obj=ca),
        Wine(producer=cara, cuvee="Escolle Vineyard", vintage="2019", type="Red", appellation=slh, region_obj=ca),
        Wine(producer=prum, cuvee="Sonnenuhr Riesling Spätlese", vintage="2015", type="White", appellation=mo, region_obj=mosel),
        Wine(producer=allemand, cuvee="Chaillots", vintage="2017", type="Red", appellation=cornas, region_obj=rhone),
        Wine(producer=chave, cuvee="Blanc", vintage="2014", type="White", appellation=herm, region_obj=rhone),
        Wine(producer=allemand, cuvee="Sans Contour", vintage="2017", type="Red", appellation=cornas, region_obj=rhone),
    ])


def test_preview_pick_and_link(client):
    def run(**body):
        client.post("/api/maintenance/vineyards", json=body)
        return wait_job(client)

    job = run(commit=False)
    assert job["status"] == "done", job
    picks = {it["label"]: it["pick"]["on"] for it in job["result"]["items"]}
    # Escolle and Chaillot in the appellation's village: ticked; Sonnenuhr (Wehlen, a Mosel wine): to check;
    # "Blanc" isn't Les Blancs, and a vineyard without an outline isn't offered
    assert picks == {"Escolle · Santa Lucia Highlands": True, "Chaillot · Cornas": True, "Wehlener Sonnenuhr · Wehlen": False}
    escolle = next(it for it in job["result"]["items"] if it["label"].startswith("Escolle"))
    assert "2 vintages" in escolle["detail"]
    assert client.get(escolle["pick"]["map"]).json()["vineyards"]["features"] == []  # no store in tests: no outline

    keys = [it["pick"]["key"] for it in job["result"]["items"] if it["pick"]["on"]]
    job = run(commit=True, keys=keys)
    assert job["status"] == "done", job
    assert "2 cuvées linked" in job["result"]["summary"] and "3 wines" in job["result"]["summary"]
    left = [it["label"] for it in run(commit=False)["result"]["items"]]
    assert left == ["Wehlener Sonnenuhr · Wehlen"]  # the linked ones aren't offered again


def test_names():
    w = vn.words
    assert vn._named(w("Les Poyeux")) and not vn._named(w("Les Blancs")) and not vn._named(w("Le Village"))
    assert vn._quality(w("Escolle Vineyard"), [w("Escolle")]) > 0
    assert vn._quality(w("Running Fence Vineyard"), [w("Fence")]) == 0  # only part of the name
