"""Settings: defaults, persistence, validation, and their effect on cellar figures."""
from db import Bottle, Producer, Region, Wine


def seed(s):
    loire = Region(name="Loire", color="#a4c96b")
    wine = Wine(producer=Producer(name="Clos Rougeard", region_obj=loire), cuvee="Le Bourg", vintage="2016",
                type="Red", region_obj=loire)
    s.add_all([
        Bottle(wine=wine, location="H3", qty=2, price=100, currency="EUR"),
        Bottle(wine=wine, location="Home", qty=1, price=100, currency="EUR"),
        Bottle(wine=wine, location="CAVE1", qty=1, price=100, currency="CHF"),
        Bottle(wine=wine, location="Paris", qty=1, price=100, currency="EUR"),
    ])


def by_location(client):
    data = client.get("/api/cellar").json()
    return {b["location"]: b for b in data["bottles"]}, {l["name"]: l for l in data["locations"]}


def test_your_settings(client):
    s = client.get("/api/settings").json()
    assert s["exchange_rates"]["EUR"] == 1.49 and s["local_label"] == "Local"
    bottles, locations = by_location(client)
    assert bottles["H3"]["price_base"] == 149
    assert bottles["Paris"]["local"] is False
    assert (locations["H3"]["group"], locations["H3"]["capacity"]) == ("Home", 10)
    assert (locations["Home"]["group"], locations["Home"]["capacity"]) == ("Home", None)
    assert locations["CAVE1"]["group"] == "Offsite"


def test_edits_apply_to_cellar_and_persist(client):
    s = client.get("/api/settings").json()
    s["exchange_rates"].update({"EUR": 1.5, "chf": 1.6})
    s["non_local_keywords"] = []
    s["storage_groups"].append({"name": "Cave", "prefix": "CAVE", "capacity": 24})
    s["other_group"] = "Elsewhere"
    saved = client.put("/api/settings", json=s).json()
    assert saved["exchange_rates"]["CHF"] == 1.6  # currency codes are upper-cased

    bottles, locations = by_location(client)
    assert bottles["H3"]["price_base"] == 150
    assert bottles["CAVE1"]["price_base"] == 160
    assert bottles["Paris"]["local"] is True
    assert (locations["CAVE1"]["group"], locations["CAVE1"]["capacity"]) == ("Cave", 24)
    assert locations["Paris"]["group"] == "Elsewhere"
    assert client.get("/api/settings").json()["storage_groups"][-1]["name"] == "Cave"


def test_validation(client):
    s = client.get("/api/settings/defaults").json()
    s["exchange_rates"]["EUR"] = 3  # the main currency stays 1
    assert client.put("/api/settings", json=s).json()["exchange_rates"]["EUR"] == 1.0
    bad_rate = {**s, "exchange_rates": {"EUR": -1}}
    assert client.put("/api/settings", json=bad_rate).status_code == 422
    dup = {**s, "storage_groups": [{"name": "A", "prefix": "H"}, {"name": "B", "prefix": "H"}]}
    assert client.put("/api/settings", json=dup).status_code == 422
    assert client.put("/api/settings", json={**s, "map_default_basemap": "nope"}).status_code == 422


def test_another_main_currency(client):
    s = client.get("/api/settings/defaults").json()
    s.update(currency="eur", exchange_rates={"CHF": 1.05, "SGD": 0.67})
    saved = client.put("/api/settings", json=s).json()
    assert saved["currency"] == "EUR" and saved["exchange_rates"]["EUR"] == 1.0  # the main one is 1
    bottles, _ = by_location(client)
    assert bottles["H3"]["price_base"] == 100  # EUR bottles as they are, CHF converted
    assert bottles["CAVE1"]["price_base"] == 105
    assert client.get("/api/lookups/options").json()["currencies"][0] == "EUR"  # offered first in the forms


def test_new_installation(client):
    """Neutral defaults, the first-start page until settings are saved, and the first critic adopted."""
    from db import get_session
    from main import app
    import settings
    session = next(app.dependency_overrides[get_session]())
    session.query(settings.AppSettingsRow).delete()
    session.commit()
    settings.refresh(session)
    session.close()
    try:
        assert client.get("/api/settings/setup").json() == {"needed": True}
        d = client.get("/api/settings").json()
        assert (d["currency"], d["storage_groups"], d["bi_location"], d["preferred_critic"]) == ("EUR", [], "", "")
        assert client.post("/api/wines/1/scores", json={"critic": " Vinous ", "score": "94"}).status_code == 200
        assert client.get("/api/settings").json()["preferred_critic"] == "Vinous"  # the first critic, saved
        assert client.get("/api/settings/setup").json() == {"needed": False}
        assert client.post("/api/wines/1/scores", json={"critic": "Jancis Robinson", "score": "17"}).status_code == 200
        assert client.get("/api/settings").json()["preferred_critic"] == "Vinous"  # not replaced
    finally:
        from conftest import TEST_SETTINGS
        session = next(app.dependency_overrides[get_session]())
        settings.save(session, TEST_SETTINGS)
        session.close()


def test_integrations(client, monkeypatch):
    for key in ("BI_EMAIL", "BI_PASSWORD", "BI_SALES_LEDGER", "BI_PURCHASE_LEDGER", "WINELABS_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    found = {i["id"]: i for i in client.get("/api/integrations").json()["integrations"]}
    assert set(found) == {"bordeaux_index", "winelabs", "lwin"} and not found["bordeaux_index"]["configured"]
    monkeypatch.setenv("WINELABS_API_KEY", "k")
    assert {i["id"]: i["configured"] for i in client.get("/api/integrations").json()["integrations"]}["winelabs"]
