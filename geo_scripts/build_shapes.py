"""Builds the unified shape store, data/geo/shapes/: one GeoParquet file per source with the same columns, from
the files the download scripts left in data/geo. The sources are declared in app/api/data/shape_sources.json: to
add one, put its files under data/geo/, add an entry there and run this with --only <name>. Rerun whenever a
source file changes.

    python geo_scripts/build_shapes.py                       # every source
    python geo_scripts/build_shapes.py --only inao,au        # some of them
    python geo_scripts/build_shapes.py --geo-dir /geo        # GEO_DIR by default, else data/geo

On a server, with the app's Docker image (it has geopandas, shapely and pyarrow; /geo is read-only in the running
container, so a throwaway one):

    docker run --rm -v "$PWD/data/geo:/geo" -v "$PWD/geo_scripts:/app/geo_scripts:ro" -e GEO_DIR=/geo \\
        <the app's image> python /app/geo_scripts/build_shapes.py

Columns: source, source_id (what a boundary link names: "<source>:<source_id>"), name, level (zone / region /
subregion where the source has one), geometry (WKB, lon/lat), display (WKB, simplified and rounded like the map
shows it), bbox_w / bbox_s / bbox_e / bbox_n.
"""
import argparse
import glob
import json
import os
import re
import sys
import time

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "app", "api"))

import shape_links  # noqa: E402
from shape_links import norm  # noqa: E402  (the app's name rules: a slug here is what its shape links look for)

SOURCES_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "api", "data", "shape_sources.json")
# The map's display simplification (app/api/geo.py), so the store's display outlines match what it shows today
DETAIL = {"appellation": (0.0005, 5), "vineyard": (0.00005, 5)}  # tolerance in degrees, coordinate decimals
RELATIVE_TOLERANCE = 1 / 2500
ROW_GROUP = 64  # rows per parquet row group (see write)
# Shapes smaller than ~75 km keep finer detail than the kind's tolerance (a 300 m grand cru isn't drawn to ~40 m):
# 1/1500 of their size, down to FINEST (~2 m)
SMALL_TOLERANCE = 1 / 1500
FINEST = 0.00002
MERGE_SHARE = 1 / 80  # the display merge reaches at most 1/80 of a shape's size: Savoie's 300 m, a grand cru's ~6 m
# A name on several levels (Tasmania is a zone and a region): the smallest level wins
LEVELS = ("subregion", "region", "zone", "state")
BATCH = 2000


def load_sources(path=SOURCES_FILE, geo_dir=None):
    """The sources (shape_sources.json, and geo_dir's sources.local.json: see shape_links.load_sources), checked."""
    sources = list(shape_links.load_sources(path, geo_dir).values())
    for spec in sources:
        missing = [k for k in ("name", "files", "kind") if not spec.get(k)]
        if missing or not (spec.get("id") or spec.get("id_from_name")) or spec["kind"] not in DETAIL:
            sys.exit(f"{path}: source {spec.get('name', '?')}: needs name, files, kind (appellation or vineyard) "
                     f"and id or id_from_name")
    return {spec["name"]: spec for spec in sources}


def slug(name):
    return norm(name).replace(" ", "-")


def _first(names, wanted):
    return next((c for c in wanted or () if c in names), None)


def _lonlat_crs(crs):
    """Whether a GeoParquet column's CRS is lon/lat (missing means OGC:CRS84, per the spec)."""
    if not crs:
        return True
    ident = crs.get("id", {}) if isinstance(crs, dict) else {}
    return (ident.get("authority"), str(ident.get("code"))) in (("EPSG", "4326"), ("OGC", "CRS84"))


def read_rows(path, spec):
    """[(id, name, level, WKB)] from one file of any format geopandas reads, in lon/lat. Lon/lat GeoParquet files
    are read without geopandas (France alone is ~100 MB)."""
    id_cols, name_cols, level_cols = spec.get("id") or [], spec.get("name_columns"), spec.get("level_columns")
    if path.endswith(".parquet"):
        import pyarrow.parquet as pq
        pf = pq.ParquetFile(path)
        names = pf.schema_arrow.names
        meta = json.loads((pf.schema_arrow.metadata or {}).get(b"geo", b"{}"))
        geom_col = meta.get("primary_column", "geometry")
        col_meta = meta.get("columns", {}).get(geom_col, {})
        lonlat = spec.get("assume_crs") in ("EPSG:4326", "OGC:CRS84") or _lonlat_crs(col_meta.get("crs"))
        if geom_col in names and col_meta.get("encoding", "WKB").upper() == "WKB" and lonlat:
            cols = {"id": _first(names, id_cols), "name": _first(names, name_cols), "level": _first(names, level_cols)}
            if id_cols and not cols["id"]:
                print(f"  [SKIP] {os.path.basename(path)}: none of {', '.join(id_cols)} in {names}")
                return []
            table = pf.read(columns=[geom_col] + [c for c in cols.values() if c])
            n = table.num_rows
            values = {k: table.column(c).to_pylist() if c else [None] * n for k, c in cols.items()}
            return list(zip(values["id"], values["name"], values["level"], table.column(geom_col).to_pylist()))
    import geopandas as gpd
    gdf = gpd.read_parquet(path) if path.endswith(".parquet") else gpd.read_file(path)
    if spec.get("assume_crs"):  # the file's own CRS tag is wrong (Weinlagen: lon/lat tagged EPSG:4324)
        gdf = gdf.set_crs(spec["assume_crs"], allow_override=True)
    if gdf.crs is not None and not gdf.crs.equals("EPSG:4326"):
        gdf = gdf.to_crs("EPSG:4326")
    names = list(gdf.columns)
    cols = {"id": _first(names, id_cols), "name": _first(names, name_cols), "level": _first(names, level_cols)}
    if id_cols and not cols["id"]:
        print(f"  [SKIP] {os.path.basename(path)}: none of {', '.join(id_cols)} in {names}")
        return []
    n = len(gdf)
    values = {k: list(gdf[c]) if c else [None] * n for k, c in cols.items()}
    return list(zip(values["id"], values["name"], values["level"],
                    [g.wkb if g is not None and not g.is_empty else None for g in gdf.geometry]))


def file_region(path, spec):
    """The region a file's ids are prefixed with (id_prefix: file): pfalz_12.parquet -> pfalz."""
    stem = os.path.splitext(os.path.basename(path))[0]
    return (spec.get("file_regions") or {}).get(stem) or re.sub(r"_\d+$", "", stem)


def source_rows(geo_dir, spec):
    """[(source_id, name, level, WKB)] for one source, once per id (the smallest level wins), and its files."""
    paths = sorted({p for pattern in spec["files"] for p in glob.glob(os.path.join(geo_dir, pattern))})
    found = {}
    for path in paths:
        prefix = file_region(path, spec) if spec.get("id_prefix") == "file" else None
        for raw_id, name, level, wkb in read_rows(path, spec):
            if wkb is None:
                continue
            if isinstance(raw_id, float):  # a shapefile id column with gaps is read as decimals: 363.0, NaN
                raw_id = int(raw_id) if raw_id == raw_id and raw_id.is_integer() else (None if raw_id != raw_id else raw_id)
            sid = slug(name) if spec.get("id_from_name") else (str(raw_id) if raw_id is not None else "")
            if not sid:
                continue
            sid = f"{prefix}:{sid}" if prefix else sid
            level = str(level).strip().lower() if level else None
            rank = LEVELS.index(level) if level in LEVELS else len(LEVELS)
            if sid not in found or rank < found[sid][1]:
                found[sid] = ((sid, str(name).strip() if name is not None else None, level, bytes(wkb)), rank)
    return [row for row, _ in found.values()], paths


def merged(geoms, meters, crs):
    """Parcels within ~2 x meters of each other fused into one zone: grown by `meters`, then shrunk back, in a
    metric projection (`crs`). Savoie's 1,630 strips of vines become 36 vineyard zones; road gaps in Gevrey close.
    Small shapes get less (MERGE_SHARE of their size), so a grand cru's corners and notches stay."""
    import geopandas as gpd
    import numpy as np
    import shapely
    shapes = gpd.GeoSeries(shapely.make_valid(geoms), crs="EPSG:4326").to_crs(crs)
    w, s, e, n = shapes.bounds.values.T
    reach = np.minimum(meters, np.hypot(e - w, n - s) * MERGE_SHARE)
    return shapes.buffer(reach, quad_segs=4).buffer(-reach, quad_segs=4).to_crs("EPSG:4326").values


def display(wkbs, tolerance, digits, merge=None):
    """[(display WKB, (w, s, e, n))] for full-detail WKBs: simplified like the map (relative to each shape's size
    too) and rounded; with merge (meters, crs), nearby parts fused first. One shapely array call per batch."""
    import numpy as np
    import shapely
    geoms = shapely.from_wkb(np.array(wkbs, dtype=object))
    w, s, e, n = shapely.bounds(geoms).T
    shown = np.array(merged(geoms, *merge), dtype=object) if merge else geoms
    size = np.hypot(e - w, n - s)
    fine = np.minimum(tolerance, np.maximum(FINEST, size * SMALL_TOLERANCE))
    small = shapely.simplify(shown, np.maximum(fine, size * RELATIVE_TOLERANCE), preserve_topology=True)
    small = shapely.transform(small, lambda c: np.round(c, digits))
    return list(zip(shapely.to_wkb(small), [tuple(map(float, b)) for b in shapely.bounds(geoms)]))


def write(out_dir, source, rows, kind, merge=None):
    """data/geo/shapes/<source>.parquet, GeoParquet (geometry and display as WKB). merge: (meters, crs) to fuse
    nearby parts in the display outline (display_merge_m / display_crs in shape_sources.json)."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    tolerance, digits = DETAIL[kind]
    shown, boxes = [], []
    for i in range(0, len(rows), BATCH):
        for wkb, box in display([r[3] for r in rows[i:i + BATCH]], tolerance, digits, merge):
            shown.append(wkb)
            boxes.append(box)
    table = pa.table({
        "source": pa.array([source] * len(rows), pa.string()),
        "source_id": pa.array([r[0] for r in rows], pa.string()),
        "name": pa.array([r[1] for r in rows], pa.string()),
        "level": pa.array([r[2] for r in rows], pa.string()),
        "geometry": pa.array([r[3] for r in rows], pa.binary()),
        "display": pa.array([bytes(g) for g in shown], pa.binary()),
        "bbox_w": pa.array([b[0] for b in boxes], pa.float64()),
        "bbox_s": pa.array([b[1] for b in boxes], pa.float64()),
        "bbox_e": pa.array([b[2] for b in boxes], pa.float64()),
        "bbox_n": pa.array([b[3] for b in boxes], pa.float64()),
    })
    # No "crs" key: GeoParquet's default, lon/lat (OGC:CRS84). An explicit null would mean "unknown"
    geo_meta = {"version": "1.0.0", "primary_column": "geometry", "columns": {
        "geometry": {"encoding": "WKB", "geometry_types": []},
        "display": {"encoding": "WKB", "geometry_types": []}}}
    table = table.replace_schema_metadata({b"geo": json.dumps(geo_meta).encode()})
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{source}.parquet")
    # Small row groups: the app reads one full outline at a time (a page's "Full detail"), only its group
    pq.write_table(table, path + ".tmp", compression="zstd", row_group_size=ROW_GROUP)
    os.replace(path + ".tmp", path)
    return path


def main(geo_dir, only=None, sources_file=SOURCES_FILE):
    sources = load_sources(sources_file, geo_dir)
    unknown = [s for s in only or () if s not in sources]
    if unknown:
        sys.exit(f"Unknown source(s): {', '.join(unknown)} (in {sources_file}: {', '.join(sources)})")
    out_dir = os.path.join(geo_dir, "shapes")
    manifest_path = os.path.join(out_dir, "manifest.json")
    try:
        with open(manifest_path) as f:
            manifest = json.load(f)
    except (OSError, ValueError):
        manifest = {}
    for name in only or sources:
        spec, started = sources[name], time.time()
        rows, inputs = source_rows(geo_dir, spec)
        if not rows:
            print(f"{name}: nothing in {geo_dir} for {', '.join(spec['files'])}")
            continue
        merge = (spec["display_merge_m"], spec.get("display_crs", "EPSG:3857")) if spec.get("display_merge_m") else None
        path = write(out_dir, name, rows, spec["kind"], merge)
        manifest[name] = {
            "file": os.path.basename(path), "rows": len(rows), "built": time.strftime("%Y-%m-%d %H:%M:%S"),
            "link": spec.get("link"),
            "inputs": [{"file": os.path.relpath(p, geo_dir), "size": os.path.getsize(p),
                        "modified": int(os.path.getmtime(p))} for p in inputs]}
        mb = os.path.getsize(path) / 1e6
        print(f"{name}: {len(rows)} shapes from {len(inputs)} file{'s' * (len(inputs) != 1)} -> "
              f"shapes/{os.path.basename(path)} ({mb:.1f} MB, {time.time() - started:.0f} s)")
    if manifest:
        os.makedirs(out_dir, exist_ok=True)
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2, sort_keys=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--geo-dir", default=os.getenv("GEO_DIR") or os.path.join(PROJECT_ROOT, "data", "geo"))
    parser.add_argument("--only", help="comma-separated source names (see shape_sources.json)")
    parser.add_argument("--sources", default=SOURCES_FILE, help="the sources file (shape_sources.json)")
    args = parser.parse_args()
    main(args.geo_dir, [s.strip() for s in args.only.split(",")] if args.only else None, args.sources)
