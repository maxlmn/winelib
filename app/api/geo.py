"""Appellation and vineyard boundaries, from the shape store (GEO_DIR/shapes/: the map pack, or outlines built alike).

Each appellation or vineyard row names its shape in `boundary` ("inao:291", "eu:PDO-IT-A0281",
"vineyard:bourgogne:1282"), filled by shape links (shape_links.py); a row without one has nothing to draw. An outline
drawn in the app is a "custom:<id>" link to the custom_shapes table (routers/outlines.py). The store
holds a display outline per shape, simplified and rounded when it was built, so nothing is simplified here:
- a source's file is read once (its ids, display outlines and boxes), the first time one of its shapes is asked for;
- an outline is turned into GeoJSON text once, kept in memory; responses are built from those strings directly;
- the map opens on one coarse outline per region, read from a prebuilt file (region_outline);
- a page's own shape can be shown at full detail (detail): the store's `geometry` column, one row read on request.
"""
import hashlib
import json
import logging
import os
import threading
from functools import lru_cache

import crus
import paths

log = logging.getLogger(__name__)

GEO_DIR = paths.GEO_DIR
SHAPES_DIR = os.getenv("SHAPES_DIR", os.path.join(GEO_DIR, "shapes"))
CACHE_VERSION = 4  # bump when the shapes sent change for another reason than the store
BBOX_DIGITS = 5


def geo_available():
    try:
        import shapely  # noqa: F401
        return True
    except ImportError:
        return False


# --- The store -------------------------------------------------------------------------------------------

_lock = threading.Lock()


@lru_cache
def _source(name):
    """{source_id: (display WKB, (w, s, e, n))} of one store file; {} when it isn't there."""
    path = os.path.join(SHAPES_DIR, f"{name}.parquet")
    if not os.path.exists(path):
        log.warning("No shape store file %s: its shapes aren't drawn", path)
        return {}
    import pyarrow.parquet as pq
    t = pq.read_table(path, columns=["source_id", "display", "bbox_w", "bbox_s", "bbox_e", "bbox_n"]).to_pydict()
    return {sid: (g, (w, s, e, n)) for sid, g, w, s, e, n in
            zip(t["source_id"], t["display"], t["bbox_w"], t["bbox_s"], t["bbox_e"], t["bbox_n"]) if g is not None}


def _lookup(boundary, session=None):
    """(display WKB, bbox) for a boundary link, or None. An outline drawn in the app is read with `session`."""
    if not boundary or ":" not in boundary:
        return None
    source, sid = boundary.split(":", 1)
    if source == "custom":
        return _custom(sid, session)
    return _source(source).get(sid)


def _custom(sid, session):
    """(display WKB, bbox) of an outline drawn in the app (the custom_shapes table), or None."""
    import shapely
    from db import CustomShape
    row = session.get(CustomShape, int(sid)) if session is not None and sid.isdigit() else None
    if row is None:
        return None
    return shapely.to_wkb(shapely.from_geojson(row.display)), tuple(float(b) for b in row.bbox.split(","))


def custom_changed(shape_id):
    """An outline drawn in the app was saved or deleted: its GeoJSON is read again next time."""
    with _lock:
        _cache.pop(f"custom:{shape_id}", None)


def outlines_installed():
    """Whether the shape store has any source (a map pack downloaded, or a store built): without, nothing can be drawn
    but the region outlines, and the map says where to get them."""
    try:
        with open(os.path.join(SHAPES_DIR, "manifest.json")) as f:
            names = list(json.load(f))
    except (OSError, ValueError):
        return False
    return any(os.path.exists(os.path.join(SHAPES_DIR, f"{n}.parquet")) for n in names)


def warm():
    """Reads the store files ahead of the first map request, in the background."""
    try:
        with open(os.path.join(SHAPES_DIR, "manifest.json")) as f:
            names = list(json.load(f))
    except (OSError, ValueError):
        return
    for name in names:
        try:
            _source(name)
        except Exception:  # a bad file: the request that needs it reports it
            log.exception("Couldn't read the %s shapes", name)
    try:
        crus.warm()
    except Exception:
        log.exception("Couldn't work out the vineyards' crus")


# boundary -> (geometry as a GeoJSON string, [west, south, east, north]), or (None, None) when there's none
_cache = {}


def reset():
    """Forgets everything read (GEO_DIR or the store changed: tests)."""
    with _lock:
        _cache.clear()
    for fn in (_source, _full_index, detail, _manifest_stamp, _region_outlines):
        fn.cache_clear()
    crus.reset()


def shapes(kind, objs):
    """[(GeoJSON string, bbox)] for these appellation or vineyard rows, in order; (None, None) for one
    without a boundary (or whose shape isn't in the store)."""
    from sqlalchemy.orm import object_session
    keys = [getattr(o, "boundary", None) for o in objs]
    todo = [k for k in dict.fromkeys(keys) if k and k not in _cache]
    if todo:
        import numpy as np
        import shapely
        custom = {k for k in todo if k.startswith("custom:")}
        sessions = {k: object_session(o) for k, o in zip(keys, objs) if k in custom}  # outlines drawn in the app
        found = [(k, _lookup(k, sessions.get(k))) for k in todo]
        hits = [(k, f) for k, f in found if f is not None]
        texts = shapely.to_geojson(shapely.from_wkb(np.array([f[0] for _, f in hits], dtype=object))) if hits else []
        with _lock:
            for k, f in found:
                _cache[k] = (None, None)
            for (k, (_, box)), text in zip(hits, texts):
                _cache[k] = (str(text), [round(float(b), BBOX_DIGITS) for b in box])
    return [_cache.get(k, (None, None)) if k else (None, None) for k in keys]


def shape(kind, obj):
    """(GeoJSON string, bbox) of one appellation or vineyard row, or (None, None) if it has no boundary."""
    return shapes(kind, [obj])[0]


# --- Full detail -----------------------------------------------------------------------------------------

DETAIL_DIGITS = 6  # ~0.1 m


@lru_cache
def _full_index(name):
    """{source_id: (row group, row)} of a store file with the full outlines; {} without (a map pack's file, which only
    has the display ones). The store's files have small row groups, so one outline reads only its own group."""
    path = os.path.join(SHAPES_DIR, f"{name}.parquet")
    if not os.path.exists(path):
        return {}
    import pyarrow.parquet as pq
    f = pq.ParquetFile(path)
    if "geometry" not in f.schema_arrow.names:
        return {}
    return {sid: (g, i) for g in range(f.num_row_groups)
            for i, sid in enumerate(f.read_row_group(g, columns=["source_id"]).column(0).to_pylist())}


def _split(boundary):
    if not boundary or ":" not in boundary or boundary.startswith("custom:"):
        return None, None
    return boundary.split(":", 1)


def has_detail(boundary):
    """Whether the store has this shape's full outline (an outline drawn in the app is shown as drawn already)."""
    source, sid = _split(boundary)
    return source is not None and sid in _full_index(source)


@lru_cache(maxsize=16)
def detail(boundary):
    """(GeoJSON string, bbox) of a shape's full outline, rounded to ~0.1 m; None when the store hasn't it."""
    source, sid = _split(boundary)
    found = _full_index(source).get(sid) if source else None
    if found is None:
        return None
    import numpy as np
    import pyarrow.parquet as pq
    import shapely
    group, row = found
    f = pq.ParquetFile(os.path.join(SHAPES_DIR, f"{source}.parquet"))
    wkb = f.read_row_group(group, columns=["geometry"]).column(0)[row].as_py()
    if wkb is None:
        return None
    g = shapely.transform(shapely.from_wkb(wkb), lambda c: np.round(c, DETAIL_DIGITS))
    return shapely.to_geojson(g), [round(float(b), BBOX_DIGITS) for b in shapely.bounds(g)]


# --- Region outlines -------------------------------------------------------------------------------------

# One coarse outline per wine region, built from Natural Earth boundaries by
# built from Natural Earth and committed: read here, never computed
REGION_OUTLINES = os.getenv("REGION_OUTLINES", os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "region_outlines.geojson"))


@lru_cache
def _region_outlines():
    """{region name: (outline as a GeoJSON string, bbox)}"""
    try:
        with open(REGION_OUTLINES, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        log.warning("No region outlines (%s): the map overview shows none", e)
        return {}
    return {f["properties"]["name"]: (json.dumps(f["geometry"], separators=(",", ":")), f["properties"]["bbox"])
            for f in data.get("features", []) if f.get("geometry")}


def region_outline(name):
    """(GeoJSON string, bbox) of a wine region's outline, or (None, None) when there's none."""
    return _region_outlines().get(name, (None, None))


# --- Responses -------------------------------------------------------------------------------------------

def _stats_props(s):
    """Cellar and tasting figures (see routers/map.map_stats)."""
    return {"bottles": s.get("bottles", 0), "value": round(s.get("value", 0)), "tastings": s.get("tastings", 0)}


def appellation_props(a, stats):
    s = stats.get(a.id, {})
    return {
        "id": a.id, "kind": "appellation", "name": a.name,
        "region": a.region_obj.name if a.region_obj else None,
        "color": (a.region_obj.color if a.region_obj else None) or "#9a9893",
        "subregion": a.subregion, "type": a.type, "cru": crus.appellation_level(a), **_stats_props(s),
    }


def vineyard_props(v, stats):
    s = stats.get(v.id, {})
    return {
        "id": v.id, "kind": "vineyard", "name": v.name, "village": v.village, "subregion": v.sub_region,
        "cru": crus.vineyard_level(v), **_stats_props(s),
    }


PROPS = {"appellation": appellation_props, "vineyard": vineyard_props}


def collection_json(kind, objs, stats):
    """A GeoJSON FeatureCollection (plus "missing": names without a boundary), as a JSON string."""
    features, missing = [], []
    found = shapes(kind, objs) if geo_available() else [(None, None)] * len(objs)
    for o, (geom, _) in zip(objs, found):
        if geom is None:
            missing.append(o.name)
        else:
            props = json.dumps(PROPS[kind](o, stats), ensure_ascii=False)
            features.append(f'{{"type":"Feature","id":{o.id},"geometry":{geom},"properties":{props}}}')
    return f'{{"type":"FeatureCollection","features":[{",".join(features)}],"missing":{json.dumps(sorted(missing), ensure_ascii=False)}}}'


@lru_cache
def _manifest_stamp():
    """Changes whenever the store changes (a new manifest.json: the map pack installed, or rebuilt)."""
    try:
        with open(os.path.join(SHAPES_DIR, "manifest.json"), "rb") as f:
            return hashlib.sha1(f.read()).hexdigest()[:16]
    except OSError:
        return "none"


def version(session=None):
    """Changes whenever any shape could: the browser keeps shapes by row id under it, so it covers the store
    (rebuilt) and, with a session, the rows' links (shape links rerun)."""
    h = hashlib.sha1(f"{CACHE_VERSION}:{_manifest_stamp()}".encode())
    if session is not None:
        from db import Appellation, CustomShape, Vineyard
        for table in (Appellation, Vineyard):
            for row_id, boundary in session.query(table.id, table.boundary).order_by(table.id):
                h.update(f"{row_id}={boundary or ''};".encode())
        # an outline drawn in the app keeps its link when it's edited: its date says it changed
        for shape_id, updated in session.query(CustomShape.id, CustomShape.updated).order_by(CustomShape.id):
            h.update(f"custom:{shape_id}@{updated};".encode())
    return h.hexdigest()[:12]


def geometries_json(kind, objs):
    """{"<id>": GeoJSON geometry, or null without a boundary}, as a JSON string. Properties travel
    separately (in the index responses), so the browser can keep geometries across visits."""
    found = shapes(kind, objs) if geo_available() else [(None, None)] * len(objs)
    return "{" + ",".join(f'"{o.id}":{g or "null"}' for o, (g, _) in zip(objs, found)) + "}"


def merge_extents(*extents):
    boxes = [e for e in extents if e]
    return [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)] if boxes else None
