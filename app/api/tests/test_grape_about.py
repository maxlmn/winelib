"""A grape's page reads data/grapes/grapes.json: by the grape's VIVC number, else its name; the app works without it."""
import json

import pytest

import grape_about
from db import Varietal

SHEET = {"title": "Savagnin blanc B", "url": "https://example.org/savagnin", "france": {"1958": 185, "2018": 568},
         "sections": [{"title": "Origin", "text": "Franche-Comté."}, {"title": "Its wines", "text": "Vins jaunes."}]}
PLANTED = {"world": {"2000": 2000, "2023": 3000}, "rank": 90, "countries": [["France", 2500]],
           "regions": [["Jura", "France", 500]]}
DATA = {"sources": [{"key": "sheet", "name": "Pl@ntGrape", "licence": "CC BY-NC-SA 4.0", "credit": "Pl@ntGrape", "url": "https://x"},
                    {"key": "planted", "name": "Adelaide", "licence": "CC BY 4.0", "credit": "Anderson", "url": "https://y"}],
        "grapes": [{"vivc": 10, "name": "Savagnin", "names": ["Savagnin"], "sheet": SHEET, "planted": PLANTED},
                   {"vivc": None, "name": "Baga", "names": ["Baga"], "planted": PLANTED}]}


def seed(s):
    s.add_all([Varietal(id=1, name="Heida", vivc=10, origin="France"), Varietal(id=2, name="Bága", vivc=99, origin="Portugal"),
               Varietal(id=3, name="Nothing Known"), Varietal(id=4, name="Muscat", vivc=10)])


@pytest.fixture
def data(tmp_path, monkeypatch):
    path = tmp_path / "grapes.json"
    monkeypatch.setattr(grape_about, "PATH", str(path))
    grape_about.reset()
    yield path
    grape_about.reset()


def test_found_by_vivc_then_name(client, data):
    data.write_text(json.dumps(DATA), encoding="utf-8")
    about = client.get("/api/grapes/1/about").json()
    assert about["found"] and about["sheet"]["title"] == "Savagnin blanc B" and about["planted"]["rank"] == 90
    assert [c["name"] for c in about["credits"]] == ["Pl@ntGrape", "Adelaide"]
    about = client.get("/api/grapes/2/about").json()
    assert about["sheet"] is None and [c["name"] for c in about["credits"]] == ["Adelaide"]  # only its sources' credits
    assert client.get("/api/grapes/3/about").json() == {"found": False}
    assert client.get("/api/grapes/4/about").json() == {"found": False}  # a family: not its one member's sheet


def test_its_origin_said_once(client, data):
    data.write_text(json.dumps(DATA), encoding="utf-8")
    assert client.get("/api/grapes/1").json()["origin"] is None  # its sheet's Origin says it
    assert client.get("/api/grapes/2").json()["origin"] == "Portugal"  # no sheet


def test_without_the_file(client, data):
    assert client.get("/api/grapes/1/about").json() == {"found": False}  # someone may remove it: its licence is its own
