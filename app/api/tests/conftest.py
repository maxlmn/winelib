"""Each test module gets its own fresh SQLite database and TestClient.

A test module defines:
    def seed(session): ...         # required: add the rows it needs (models from `db`)
    def write_geo(geo_dir): ...    # optional: write parquet fixtures; GEO_DIR points there for the module
and uses the module-scoped `client` fixture. Modules never see each other's rows.
"""
import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

API_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, API_DIR)

import db  # noqa: E402
import geo  # noqa: E402
import paths  # noqa: E402
import settings  # noqa: E402
import wiki  # noqa: E402
from main import app  # noqa: E402


# The settings the tests run with, as an installation that has saved its own: a main currency other than the bottles'
# (conversions), a local area, two storage groups, a Bordeaux Index location
TEST_SETTINGS = settings.Settings(
    currency="SGD",
    exchange_rates={"SGD": 1.0, "EUR": 1.49, "USD": 1.28, "GBP": 1.71, "AUD": 0.9},
    local_label="Local",
    non_local_keywords=["Paris", "Lyon", "Beaune", "Bonded"],
    bi_location="Bonded",
    storage_groups=[{"name": "Home", "prefix": "H", "capacity": 10}, {"name": "Wine bank", "prefix": "WB", "capacity": 12}],
    other_group="Offsite",
    map_default_region="Loire",
    map_default_basemap="plain",
    preferred_critic="Robert Parker",
)


def _forget_bi():
    from winelib_utils import bordeaux_index
    bordeaux_index.forget_portfolio()  # a module's fake portfolio mustn't leak into the next


@pytest.fixture(scope="module")
def client(request, tmp_path_factory):
    tmp = tmp_path_factory.mktemp(request.module.__name__)
    engine = create_engine(f"sqlite:///{tmp / 'test.db'}", connect_args={"check_same_thread": False})
    db.Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    with Session() as s:
        request.module.seed(s)
        s.commit()
        settings.save(s, TEST_SETTINGS)  # as an existing installation: its settings saved (a test can delete them)

    geo_dir = tmp / "geo"
    geo_dir.mkdir()
    if hasattr(request.module, "write_geo"):
        request.module.write_geo(str(geo_dir))
    old_geo = geo.GEO_DIR, paths.CACHE_DIR, geo.SHAPES_DIR
    geo.GEO_DIR, paths.CACHE_DIR, geo.SHAPES_DIR = str(geo_dir), str(tmp / "geo_cache"), str(geo_dir / "shapes")
    geo.reset()
    wiki.reset()
    _forget_bi()

    def get_session():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    settings.apply(TEST_SETTINGS)  # a module that edits settings must not leak into the next
    app.dependency_overrides[db.get_session] = get_session
    yield TestClient(app)
    app.dependency_overrides.pop(db.get_session, None)
    settings.apply(TEST_SETTINGS)
    geo.GEO_DIR, paths.CACHE_DIR, geo.SHAPES_DIR = old_geo
    geo.reset()
    wiki.reset()
    _forget_bi()
    engine.dispose()


@pytest.fixture
def fetch_price(client):
    """The market price button, confirmed: the preview, then a save of every price it proposed. The preview with
    this bottle's saved last_price and last_price_source (None when it found none)."""
    def run(bottle_id):
        r = client.post(f"/api/bottles/{bottle_id}/market-price").json()
        found = [{"bottle_id": p["bottle_id"], "price": p["new"], "source": p["source"]}
                 for p in r["prices"] if p["new"] is not None]
        if found:
            assert client.post(f"/api/bottles/{bottle_id}/market-price/save", json={"prices": found}).status_code == 200
        this = next(p for p in r["prices"] if p["this"])
        return {**r, "last_price": this["new"], "last_price_source": this["source"],
                "others_updated": sum(1 for p in r["prices"] if not p["this"] and p["new"] is not None)}
    return run


def local_sources(geo_dir):
    """Puts an installation's own sources.local.json in geo_dir (tests/data/: a vineyard source with region files
    next to INAO's premiers crus, like Weinlagen-info's): the shipped shape_sources.json only has the premiers crus."""
    import shutil
    os.makedirs(geo_dir, exist_ok=True)
    shutil.copy(os.path.join(API_DIR, "tests", "data", "sources.local.json"), os.path.join(geo_dir, "sources.local.json"))


def write_store(geo_dir, source, shapes, kind="appellation"):
    """Writes data/geo/shapes/<source>.parquet as geo_scripts/build_shapes.py does: shapes is {source_id: geometry}."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "build_shapes", os.path.join(API_DIR, "..", "..", "geo_scripts", "build_shapes.py"))
    build = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build)
    build.write(os.path.join(geo_dir, "shapes"), source, [(sid, sid, None, g.wkb) for sid, g in shapes.items()], kind)
    path = os.path.join(geo_dir, "shapes", "manifest.json")
    import json
    manifest = json.load(open(path)) if os.path.exists(path) else {}
    manifest[source] = {"file": f"{source}.parquet", "rows": len(shapes)}
    with open(path, "w") as f:
        json.dump(manifest, f)


def rp_of(wine, field="score"):
    """Robert Parker's score (or "note", "url") on a wine page's JSON, from its scores list; None for none and for
    "-" (searched, none found)."""
    s = next((s for s in wine.get("scores", []) if s["critic"] == "Robert Parker"), None)
    value = s[field] if s else None
    return None if value in ("-", "") else value


def rp(score, note=None, url=None):
    """A wine's scores with Robert Parker's (a critic like any other in the app): Wine(..., scores=rp("95"))."""
    return [db.CriticScore(critic="Robert Parker", score=score, note=note, url=url)]
