"""Map overview: a region whose appellations have no shape (Japan) is still listed, by its own outline."""
from db import Appellation, Region


def seed(s):
    japan = Region(name="Japan", country="Japan")
    s.add_all([japan, Appellation(name="Yamanashi-ken", region_obj=japan), Region(name="Atlantis", country="Nowhere")])


def test_region_with_only_an_outline_is_listed(client):
    names = [r["name"] for r in client.get("/api/map/regions").json()]
    assert names == ["Japan"]  # Atlantis: no outline, nothing to map
    overview = client.get("/api/map/overview").json()
    (japan,) = overview["features"]
    assert japan["geometry"] and japan["properties"]["appellations"] == 0
    assert client.get(f"/api/map/regions/{japan['id']}").json()["extent"]
    assert overview["outlines"] is False  # no shape store: the map says where to get outlines
