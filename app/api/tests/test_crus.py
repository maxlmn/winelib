"""Grand / premier cru levels on the map's shapes (crus.py): appellations by name, vineyards by where they lie."""
from db import Appellation, Region, Vineyard

import crus

IDS = {}


def seed(s):
    b = Region(name="Bourgogne", country="France")
    rows = dict(
        chambertin=Appellation(name="Chambertin", region_obj=b, boundary="inao_denom:Chambertin"),
        gevrey_pc=Appellation(name="Gevrey-Chambertin Premier Cru", region_obj=b, boundary="inao_denom:Chambertin"),
        gevrey=Appellation(name="Gevrey-Chambertin", region_obj=b, boundary="inao_denom:Chambertin"),
        alsace=Appellation(name="Alsace grand cru Schlossberg", region_obj=b, boundary="inao_denom:Chambertin"),
        emilion=Appellation(name="Saint-Émilion Grand Cru", region_obj=b, boundary="inao_denom:Chambertin"),
        in_gc=Vineyard(name="Clos de Bèze", region_obj=b, boundary="vineyard:bourgogne:1"),
        in_pc=Vineyard(name="Les Cazetiers", region_obj=b, boundary="vineyard:bourgogne:2"),
        village=Vineyard(name="En Champs", region_obj=b, boundary="vineyard:bourgogne:3"),
        climat=Vineyard(name="Clos Saint-Jacques", region_obj=b, boundary="vineyard:inao-pc:4"),
    )
    s.add_all(rows.values())
    s.flush()
    IDS.update({k: r.id for k, r in rows.items()}, region=b.id)


def write_geo(geo_dir):
    from shapely.geometry import box
    from tests.conftest import write_store
    # INAO: the premier cru covers its grand cru too (declassifiable), as INAO lists it
    write_store(geo_dir, "inao_denom", {"Chambertin": box(4.0, 47.0, 4.01, 47.01),
                                        "Gevrey-Chambertin premier cru": box(4.0, 47.0, 4.03, 47.01)})
    write_store(geo_dir, "vineyard", {"bourgogne:1": box(4.002, 47.002, 4.008, 47.008),   # in the grand cru
                                      "bourgogne:2": box(4.015, 47.002, 4.025, 47.008),   # in the premier cru only
                                      "bourgogne:3": box(4.1, 47.1, 4.11, 47.11),         # elsewhere
                                      "inao-pc:4": box(4.005, 47.002, 4.012, 47.008)}, "vineyard")


def test_names():
    assert [crus.name_level(n) for n in ("Chambertin", "Clos de Vougeot ou Clos Vougeot", "Chablis Grand Cru",
                                         "Gevrey-Chambertin 1er Cru", "Meursault Premier Cru", "Meursault",
                                         "Saint-Emilion Grand Cru")] == [2, 2, 2, 1, 1, 0, 0]


def test_map_shapes_carry_the_cru(client):
    data = client.get(f"/api/map/regions/{IDS['region']}").json()
    apps = {a["name"]: a["cru"] for a in data["appellations"]}
    assert apps == {"Chambertin": 2, "Gevrey-Chambertin Premier Cru": 1, "Gevrey-Chambertin": 0,
                    "Alsace grand cru Schlossberg": 2, "Saint-Émilion Grand Cru": 0}
    levels = {v["name"]: v["cru"] for v in data["vineyards"]}
    # an INAO premier cru climat stays a premier cru even where it straddles a grand cru
    assert levels == {"Clos de Bèze": 2, "Les Cazetiers": 1, "En Champs": 0, "Clos Saint-Jacques": 1}
    shapes = client.get(f"/api/appellations/{IDS['chambertin']}/shapes").json()  # detail pages' maps too
    assert shapes["appellations"]["features"][0]["properties"]["cru"] == 2


def test_champagne_crus_by_their_level(tmp_path, monkeypatch):
    """A Champagne cru village is shaded by the store's own level; the mentions' appellations by their name."""
    from shapely.geometry import box
    import geo
    from tests.conftest import write_shapes
    write_shapes(str(tmp_path), "champagne_cru", [("51030", "Aÿ", "grand cru", box(4.0, 49.0, 4.01, 49.01).wkb),
                                                 ("51348", "Mareuil-sur-Aÿ", "premier cru", box(4.02, 49.0, 4.03, 49.01).wkb)],
                 "vineyard")
    monkeypatch.setattr(geo, "SHAPES_DIR", str(tmp_path))
    crus.reset()
    try:
        levels = [crus.vineyard_level(Vineyard(name=n, boundary=b)) for n, b in (
            ("Aÿ", "champagne_cru:51030"), ("Mareuil-sur-Aÿ", "champagne_cru:51348"), ("Nowhere", "champagne_cru:99"))]
        assert levels == [2, 1, 0]
        assert [crus.name_level(n) for n in ("Champagne Grand Cru", "Champagne Premier Cru", "Champagne")] == [2, 1, 0]
    finally:
        crus.reset()
