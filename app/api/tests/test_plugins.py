"""plugins.py: a plug-in's router, wine action and Maintenance task, from a package in the plug-ins folder."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import plugins
from db import Producer, Wine
from routers import maintenance

PLUGIN = '''
from fastapi import APIRouter

router = APIRouter()


@router.post("/api/plugins/demo/wines/{wine_id}/ping")
def ping(wine_id: int):
    return {"message": f"pong {wine_id}", "reload": False}


def register(api):
    api.include_router(router)
    api.wine_action("ping", "Ping", "/api/plugins/demo/wines/{id}/ping", critic="Demo", show=lambda w: w.vintage == "2019")
    api.maintenance_task("demo", group="Demo", title="Demo task", fn=lambda session, job: {"summary": "ok"},
                         preview=False, writes=False, description="A plug-in's task.")
'''


def seed(s):
    p = Producer(name="Clos Rougeard")
    s.add_all([Wine(producer=p, cuvee="Le Bourg", vintage="2019"), Wine(producer=p, cuvee="Le Bourg", vintage="2018")])


@pytest.fixture
def demo(tmp_path, monkeypatch):
    (tmp_path / "demo").mkdir()
    (tmp_path / "demo" / "__init__.py").write_text(PLUGIN)
    (tmp_path / "broken").mkdir()
    (tmp_path / "broken" / "__init__.py").write_text("raise ValueError('nope')")
    monkeypatch.setattr(plugins, "actions", list(plugins.actions))
    monkeypatch.setattr(plugins, "loaded", [])
    monkeypatch.setattr(maintenance, "TASKS", dict(maintenance.TASKS))
    monkeypatch.setattr(maintenance, "GROUPS", list(maintenance.GROUPS))
    app = FastAPI()
    plugins.load(app, str(tmp_path))
    return TestClient(app)


def test_a_plugin_adds_its_router_action_and_task(client, demo):
    assert demo.post("/api/plugins/demo/wines/1/ping").json() == {"message": "pong 1", "reload": False}
    wine = client.get("/api/wines/1").json()
    assert [a for a in wine["actions"] if a["id"] == "ping"] == [{
        "id": "ping", "label": "Ping", "endpoint": "/api/plugins/demo/wines/1/ping", "critic": "Demo", "busy": None,
        "confirm": None}]
    assert not [a for a in client.get("/api/wines/2").json()["actions"] if a["id"] == "ping"]  # not for the 2018
    m = client.get("/api/maintenance").json()
    assert "Demo" in m["groups"] and {"id": "demo", "group": "Demo"}.items() <= next(
        t for t in m["tasks"] if t["id"] == "demo").items()


def test_a_broken_plugin_is_left_out(demo):
    assert [(p["name"], p["ok"]) for p in plugins.loaded] == [("broken", False), ("demo", True)]
    assert plugins.loaded[0]["error"] == "ValueError: nope"
