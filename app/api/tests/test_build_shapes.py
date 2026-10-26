"""geo_scripts/build_shapes.py: today's source files in data/geo -> one GeoParquet file per source, same columns."""
import importlib.util
import json
import math
import os

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


@pytest.fixture(scope="module")
def build():
    spec = importlib.util.spec_from_file_location("build_shapes", os.path.join(ROOT, "geo_scripts", "build_shapes.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def circle(x, y, r, n=400):
    """A detailed polygon (n points), so the display version visibly drops points."""
    from shapely.geometry import Polygon
    return Polygon([(x + r * math.cos(2 * math.pi * k / n), y + r * math.sin(2 * math.pi * k / n)) for k in range(n)])


@pytest.fixture(scope="module")
def geo_dir(tmp_path_factory):
    import geopandas as gpd
    d = tmp_path_factory.mktemp("geo")
    gpd.GeoDataFrame({"id_app": [101, 102], "app": ["Chinon", "Bourgueil"]},
                     geometry=[circle(0.2, 47.1, 0.1), circle(0.1, 47.3, 0.1)], crs=4326).to_parquet(d / "france.parquet")
    gpd.GeoDataFrame({"pdo_id": ["PDO-IT-A1234"], "name": ["Barolo"]},
                     geometry=[circle(7.9, 44.6, 0.05)], crs=4326).to_parquet(d / "italy_pdo.parquet")
    gpd.GeoDataFrame({"pdo_id": ["PDO-FR-A0001", "PDO-IT-A1234"], "name": ["Chinon", "Barolo (again)"]},
                     geometry=[circle(0.2, 47.1, 0.1), circle(7.9, 44.6, 0.05)], crs=4326).to_parquet(d / "france_pdo.parquet")
    gpd.GeoDataFrame({"ava_id": ["napa_valley"], "name": ["Napa Valley"]},
                     geometry=[circle(-122.3, 38.4, 0.2)], crs=4326).to_parquet(d / "us_avas_combined.parquet")
    (d / "vineyards").mkdir()
    gpd.GeoDataFrame({"id": [7, 8], "name": ["Kirchenstück", "Jesuitengarten"]},
                     geometry=[circle(8.17, 49.4, 0.002), circle(8.18, 49.41, 0.002)], crs=4326).to_parquet(d / "vineyards" / "pfalz_12.parquet")
    gpd.GeoDataFrame({"id": [7], "name": ["Les Amoureuses"]},  # the same id as in Pfalz: kept apart by region
                     geometry=[circle(4.95, 47.18, 0.002)], crs=4326).to_parquet(d / "vineyards" / "vineyards_premier_crus_inao.parquet")
    (d / "australia").mkdir()
    sq = lambda x, y, s: {"type": "Polygon", "coordinates": [[[x, y], [x + s, y], [x + s, y + s], [x, y + s], [x, y]]]}
    json.dump({"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"GI_NAME": "Barossa Valley", "GI_TYPE": "region"}, "geometry": sq(138.9, -34.6, 0.2)},
        {"type": "Feature", "properties": {"GI_NAME": "Tasmania", "GI_TYPE": "zone"}, "geometry": sq(144, -44, 4)},
        {"type": "Feature", "properties": {"GI_NAME": "Tasmania", "GI_TYPE": "region"}, "geometry": sq(145, -43, 2)},
    ]}, open(d / "australia" / "gis.geojson", "w"))
    from tests.conftest import local_sources
    local_sources(str(d))  # the Pfalz file is Weinlagen-info's: the vineyard source of sources.local.json
    return d


def test_local_sources_replace_the_shipped_ones(geo_dir, tmp_path):
    """The shipped vineyard source is INAO's premiers crus; sources.local.json's, of the same name, replaces it in
    its place; a new name is added."""
    import json as _json
    import shape_links
    names = list(shape_links.load_sources())
    assert shape_links.load_sources()["vineyard"]["files"] == ["vineyards/vineyards_premier_crus_inao.parquet"]
    merged = shape_links.load_sources(geo_dir=str(geo_dir))
    assert merged["vineyard"]["files"] == ["vineyards/*.parquet"] and list(merged) == names
    (tmp_path / "sources.local.json").write_text(_json.dumps({"sources": [{"name": "mine", "files": ["mine/*.geojson"]}]}))
    assert list(shape_links.load_sources(geo_dir=str(tmp_path))) == names + ["mine"]


def read(path):
    import pyarrow.parquet as pq
    return pq.read_table(path).to_pylist()


def test_one_file_per_source_with_the_same_columns(build, geo_dir):
    build.main(str(geo_dir))
    shapes = geo_dir / "shapes"
    assert sorted(os.listdir(shapes)) == ["au.parquet", "ava.parquet", "eu.parquet", "inao.parquet", "manifest.json",
                                          "vineyard.parquet"]
    columns = ["source", "source_id", "name", "level", "geometry", "display", "bbox_w", "bbox_s", "bbox_e", "bbox_n"]
    for f in ("au", "ava", "eu", "inao", "vineyard"):
        rows = read(shapes / f"{f}.parquet")
        assert rows and list(rows[0]) == columns and {r["source"] for r in rows} == {f}

    assert {(r["source_id"], r["name"]) for r in read(shapes / "inao.parquet")} == {("101", "Chinon"), ("102", "Bourgueil")}
    eu = read(shapes / "eu.parquet")
    assert sorted(r["source_id"] for r in eu) == ["PDO-FR-A0001", "PDO-IT-A1234"]  # once each, across files
    # the premier crus get their own key: their ids collide with Weinlagen's Bourgogne ones
    assert {r["source_id"] for r in read(shapes / "vineyard.parquet")} == {"pfalz:7", "pfalz:8", "inao-pc:7"}
    au = {r["source_id"]: r for r in read(shapes / "au.parquet")}
    assert set(au) == {"barossa-valley", "tasmania"} and au["tasmania"]["level"] == "region"  # the smaller one
    assert au["barossa-valley"]["name"] == "Barossa Valley"


def test_display_outlines_are_simplified_and_bbox_is_the_shape(build, geo_dir):
    import shapely
    build.main(str(geo_dir), ["inao"])
    (chinon, _) = sorted(read(geo_dir / "shapes" / "inao.parquet"), key=lambda r: r["source_id"])
    full, shown = shapely.from_wkb(chinon["geometry"]), shapely.from_wkb(chinon["display"])
    assert shapely.get_num_coordinates(shown) < shapely.get_num_coordinates(full) / 4
    assert shown.symmetric_difference(full).area < full.area * 0.02  # still the same shape
    assert (chinon["bbox_w"], chinon["bbox_n"]) == pytest.approx((0.1, 47.2), abs=1e-6)
    # Readable as GeoParquet, in lon/lat
    import geopandas as gpd
    gdf = gpd.read_parquet(geo_dir / "shapes" / "inao.parquet")
    assert len(gdf) == 2 and gdf.crs is not None and gdf.crs.equals("OGC:CRS84")


def test_manifest_and_missing_sources(build, tmp_path, geo_dir):
    manifest = json.load(open(geo_dir / "shapes" / "manifest.json"))
    assert manifest["eu"]["rows"] == 2 and [i["file"] for i in manifest["eu"]["inputs"]] == ["france_pdo.parquet",
                                                                                             "italy_pdo.parquet"]
    build.main(str(tmp_path), ["ava"])  # nothing downloaded: nothing written
    assert not (tmp_path / "shapes").exists()


def test_a_new_source_is_just_files_and_an_entry(build, geo_dir, tmp_path):
    """New Zealand from a GeoPackage in the national projection (NZTM): converted to lon/lat, ids from names."""
    import geopandas as gpd
    import shapely
    from shapely.geometry import box
    (geo_dir / "new_zealand").mkdir()
    marl = gpd.GeoDataFrame({"gi": ["Marlborough", "Marlborough"], "kind": ["Region", "Zone"]},
                            geometry=[box(173.6, -41.7, 174.2, -41.4), box(172, -42.5, 175, -41)], crs=4326)
    marl.to_crs(2193).to_file(geo_dir / "new_zealand" / "gis.gpkg")
    sources = json.load(open(os.path.join(ROOT, "app", "api", "data", "shape_sources.json")))
    sources["sources"].append({"name": "nz", "files": ["new_zealand/*.gpkg"], "id_from_name": True,
                               "name_columns": ["gi"], "level_columns": ["kind"], "kind": "appellation",
                               "link": {"table": "appellations", "by": "name", "country": "New Zealand"}})
    json.dump(sources, open(tmp_path / "sources.json", "w"))

    build.main(str(geo_dir), ["nz"], str(tmp_path / "sources.json"))
    (row,) = read(geo_dir / "shapes" / "nz.parquet")
    assert (row["source_id"], row["name"], row["level"]) == ("marlborough", "Marlborough", "region")
    assert (row["bbox_w"], row["bbox_s"], row["bbox_e"], row["bbox_n"]) == pytest.approx((173.6, -41.7, 174.2, -41.4), abs=1e-4)
    assert shapely.from_wkb(row["display"]).bounds == pytest.approx((173.6, -41.7, 174.2, -41.4), abs=1e-3)
    manifest = json.load(open(geo_dir / "shapes" / "manifest.json"))
    assert manifest["nz"]["link"] == {"table": "appellations", "by": "name", "country": "New Zealand"}
    assert manifest["inao"]["rows"] == 2  # the other sources' entries are kept


def test_unknown_or_incomplete_sources_are_refused(build, geo_dir, tmp_path):
    with pytest.raises(SystemExit, match="Unknown source"):
        build.main(str(geo_dir), ["atlantis"])
    json.dump({"sources": [{"name": "x", "files": ["*.shp"], "kind": "appellation"}]}, open(tmp_path / "bad.json", "w"))
    with pytest.raises(SystemExit, match="needs name, files, kind"):
        build.main(str(geo_dir), None, str(tmp_path / "bad.json"))


def test_assume_crs_reads_a_mistagged_file_as_lon_lat(build, tmp_path):
    """Weinlagen's files are plain lon/lat tagged EPSG:4324 (WGS 72BE): converting them shifts a vineyard ~17 m."""
    import geopandas as gpd
    import pyarrow.parquet as pq
    d = tmp_path / "geo"
    (d / "vineyards").mkdir(parents=True)
    gpd.GeoDataFrame({"id": [7]}, geometry=[circle(-0.48, 47.2, 0.001)], crs="EPSG:4324").to_parquet(
        d / "vineyards" / "loire_57.parquet")
    for assume, expected_shift in ((None, True), ("EPSG:4326", False)):
        spec = {"name": "vineyard", "files": ["vineyards/*.parquet"], "id": ["id"], "kind": "vineyard", "id_prefix": "file"}
        if assume:
            spec["assume_crs"] = assume
        sources = tmp_path / f"sources_{assume is not None}.json"
        sources.write_text(json.dumps({"sources": [spec]}))
        build.main(str(d), ["vineyard"], str(sources))
        w = pq.read_table(d / "shapes" / "vineyard.parquet", columns=["bbox_w"]).column(0)[0].as_py()
        assert (abs(w - (-0.481)) > 1e-4) == expected_shift


def test_display_merge_fuses_nearby_parcels(build):
    """Two parcels 100 m apart become one display shape with a 300 m merge; the stored geometry stays as it was."""
    import shapely
    from shapely.geometry import box
    a, b = box(5.8000, 45.5, 5.9100, 45.6), box(5.9113, 45.5, 6.0200, 45.6)  # ~100 m apart, 17 km across
    parcels = shapely.MultiPolygon([a, b])
    (plain, _), = build.display([parcels.wkb], 0.0005, 4)
    (fused, _), = build.display([parcels.wkb], 0.0005, 4, (300, "EPSG:2154"))
    assert len(shapely.get_parts(shapely.from_wkb(plain))) == 2
    assert len(shapely.get_parts(shapely.from_wkb(fused))) == 1


def test_small_shapes_keep_their_detail(build):
    """A 300 m grand cru with a 30 m notch keeps it: neither the merge nor the appellation tolerance (~40 m) fills it."""
    import shapely
    from shapely.geometry import box
    d = 0.00027  # ~30 m at 45°N in longitude... and ~30 m in latitude
    plot = shapely.difference(box(5.0, 45.0, 5.004, 45.0027), box(5.002 - d / 2, 45.0027 - 3 * d, 5.002 + d / 2, 45.0027))
    (shown, _), = build.display([plot.wkb], 0.0005, 5, (300, "EPSG:2154"))
    assert shapely.from_wkb(shown).area == pytest.approx(plot.area, rel=0.02)
