"""Fill from photos (tasks/from_photos.py): a bottle's labels read by Claude, then matched against the database.
Claude isn't called: its client is replaced. Run from app/api:  pytest"""
import base64
import json
from types import SimpleNamespace

import anthropic
import pytest

from db import Appellation, Producer, Region, Wine
from tasks import from_photos

JPEG = base64.b64encode(b"\xff\xd8\xff\xe0 a photo").decode()


def seed(s):
    champagne, loire = Region(name="Champagne"), Region(name="Loire")
    ch = Appellation(name="Champagne", region_obj=champagne)
    sc = Appellation(name="Saumur-Champigny", region_obj=loire)
    krug, rougeard = Producer(name="Krug"), Producer(name="Clos Rougeard")
    s.add_all([Wine(producer=krug, cuvee="Grande Cuvée", vintage="NV", type="Bubbles", appellation=ch,
                    region_obj=champagne, disgorgement_date="Oct 2022"),
               Wine(producer=rougeard, cuvee="Le Bourg", vintage="2016", type="Red", appellation=sc, region_obj=loire)])


def reading(**fields):
    return {"producer": "", "cuvee": "", "vintage": "", "appellation": "", "region": "", "country": "", "colour": "",
            "size": "", "disgorgement": "", "grapes": [], "not_read": [], "note": "", **fields}


class FakeClient:
    """anthropic.Anthropic's stand-in: the request kept, the reading given back as the JSON text Claude writes."""
    sent, answer, stop = None, None, "end_turn"

    def __init__(self, api_key):
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self.create))

    def create(self, **kw):
        FakeClient.sent = kw
        return SimpleNamespace(stop_reason=FakeClient.stop,
                               content=[SimpleNamespace(type="text", text=json.dumps(FakeClient.answer))])


@pytest.fixture
def claude(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(anthropic, "Anthropic", FakeClient)
    FakeClient.stop = "end_turn"
    return FakeClient


def test_a_new_disgorgement_of_a_known_champagne(client, claude):
    claude.answer = reading(producer="KRUG", cuvee="Grande Cuvée", vintage="NV", appellation="Champagne",
                            colour="Bubbles", size="75cl", disgorgement="Mar 2024", not_read=["vintage"],
                            note="No year on the labels")
    r = client.post("/api/lookups/from-photos", json={"photos": [
        {"side": "back", "media_type": "image/jpeg", "data": JPEG},
        {"side": "front", "media_type": "image/jpeg", "data": JPEG}]})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["producer"]["name"] == "Krug" and d["producer"]["id"] and d["cuvee"] == "Grande Cuvée"
    assert (d["vintage"], d["type"], d["size"], d["disgorgement_date"]) == ("NV", "Bubbles", "75cl", "Mar 2024")
    assert d["wine_id"] is None and d["like_id"]  # another disgorgement of the one in WineLib: a new one of it
    assert d["not_read"] == ["vintage"] and d["note"] == "No year on the labels"
    assert d["qty"] is None and d["price"] is None  # nothing a label says
    # the front first, each photo said which it is, the answer held to the schema
    content = claude.sent["messages"][0]["content"]
    assert [b["text"] for b in content if b["type"] == "text"][:2] == ["The front label:", "The back label:"]
    assert sum(b["type"] == "image" for b in content) == 2
    assert claude.sent["output_config"]["format"]["schema"] == from_photos.SCHEMA


def test_the_same_disgorgement_is_that_wine(client, claude):
    claude.answer = reading(producer="Krug", cuvee="Grande Cuvée", vintage="NV", colour="Bubbles", disgorgement="oct 2022")
    d = client.post("/api/lookups/from-photos", json={"photos": [{"media_type": "image/jpeg", "data": JPEG}]}).json()
    assert d["wine_id"]


def test_the_appellation_as_printed_and_an_unknown_producer(client, claude):
    claude.answer = reading(producer="Domaine Inconnu", cuvee="", vintage="2019",
                            appellation="Appellation Saumur-Champigny Contrôlée", colour="Red")
    d = client.post("/api/lookups/from-photos", json={"photos": [{"media_type": "image/jpeg", "data": JPEG}]}).json()
    assert d["producer"] == {"id": None, "name": "Domaine Inconnu"}
    assert d["appellation"]["name"] == "Saumur-Champigny" and d["region"]["name"] == "Loire"
    assert d["vintage"] == "2019" and d["wine_id"] is None and d["like_id"] is None


def test_that_very_wine_and_an_odd_vintage(client, claude):
    claude.answer = reading(producer="Clos Rougeard", cuvee="Le Bourg", vintage="2016", appellation="Saumur-Champigny")
    d = client.post("/api/lookups/from-photos", json={"photos": [{"media_type": "image/jpeg", "data": JPEG}]}).json()
    assert d["wine_id"]
    claude.answer = reading(producer="Clos Rougeard", vintage="circa 1990")
    assert client.post("/api/lookups/from-photos",
                       json={"photos": [{"media_type": "image/jpeg", "data": JPEG}]}).json()["vintage"] == ""


def test_what_is_refused(client, claude, monkeypatch):
    post = lambda photos: client.post("/api/lookups/from-photos", json={"photos": photos})  # noqa: E731
    photo = {"media_type": "image/jpeg", "data": JPEG}
    assert post([]).status_code == 422
    assert post([photo, photo, photo]).status_code == 422  # two at most
    assert post([{"media_type": "image/gif", "data": JPEG}]).status_code == 422
    assert post([{"media_type": "image/jpeg", "data": "not base64!"}]).status_code == 422
    claude.stop = "refusal"
    assert post([photo]).status_code == 422
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    r = post([photo])
    assert r.status_code == 422 and "ANTHROPIC_API_KEY" in r.json()["detail"]


def test_the_form_knows_whether_a_key_is_set(client, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert client.get("/api/lookups/options").json()["label_photos"] is False
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    assert client.get("/api/lookups/options").json()["label_photos"] is True
