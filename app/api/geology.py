"""A vineyard's geology: the rock formations under its outline and the share of each.

- In France, BRGM's 1:50,000 geological maps (vectorised and harmonised by departement; Licence Ouverte 2.0, credit
  "BRGM"), shipped in the map pack as shapes/geology.parquet: the formations around the wine lieux-dits
  (geo_scripts/etl_geology.py), each with its map notation ("j3a"), its description as published and its colour.
  Worked out on each request from the few row groups of the file around the vineyard (milliseconds; only each
  group's box stays in memory).
- Elsewhere, Macrostrat's map at the outline's centre (macrostrat.org, CC BY 4.0): its most detailed map there, often
  regional (1:1,000,000 in Europe). Asked once, kept in `geologies` (routers/geology.py).
"""
import functools
import json
import os
import threading
from urllib.request import Request, urlopen

import geo

MACROSTRAT = "https://macrostrat.org/api/v2/geologic_units/map?lat={lat:.5f}&lng={lng:.5f}"
SCALES = {"large": "1:24,000 to 1:100,000", "medium": "about 1:1,000,000", "small": "about 1:5,000,000",
          "tiny": "about 1:15,000,000"}
MIN_SHARE = 0.01  # a sliver along an edge isn't the vineyard's rock

_lock = threading.Lock()
_loaded = {"stamp": None, "boxes": None}


def _path():
    return os.path.join(geo.SHAPES_DIR, "geology.parquet")


def _index():
    """(path, stamp, [(west, south, east, north)] of each row group) of the pack's geology file, read again when it
    changes; None without it. Only these boxes stay in memory (a few kilobytes): a vineyard's formations are read from
    the few row groups around it (etl_geology.py writes the file sorted by place, in groups of ~1,000)."""
    import pyarrow.parquet as pq
    import shapely
    path = _path()
    try:
        stamp = os.stat(path).st_mtime_ns
    except OSError:
        return None
    with _lock:
        if _loaded["stamp"] != stamp:
            f = pq.ParquetFile(path)
            names = f.schema_arrow.names
            boxes = []
            for g in range(f.num_row_groups):
                if "bbox_w" in names:
                    t = f.read_row_group(g, columns=["bbox_w", "bbox_s", "bbox_e", "bbox_n"])
                    w, s_, e, n = (t.column(c).to_numpy() for c in ("bbox_w", "bbox_s", "bbox_e", "bbox_n"))
                    boxes.append((w.min(), s_.min(), e.max(), n.max()))
                else:  # a file without its boxes (an older one): from the outlines
                    geoms = shapely.from_wkb(f.read_row_group(g, columns=["display"]).column(0).to_numpy(
                        zero_copy_only=False))
                    boxes.append(tuple(shapely.total_bounds(geoms)))
            _loaded.update(stamp=stamp, boxes=boxes)
            _group.cache_clear()
        return path, stamp, _loaded["boxes"]


@functools.lru_cache(maxsize=8)
def _group(path, stamp, g):
    """One row group's formations: (geometries, [(notation, descr, colour)]); the last few kept (a page's wine and
    vineyard ask for the same ones)"""
    import pyarrow.parquet as pq
    import shapely
    t = pq.ParquetFile(path).read_row_group(g, columns=["notation", "descr", "colour", "display"])
    geoms = shapely.from_wkb(t.column("display").to_numpy(zero_copy_only=False))
    return geoms, list(zip(t.column("notation").to_pylist(), t.column("descr").to_pylist(),
                           t.column("colour").to_pylist()))


def brgm(outline):
    """[{"notation", "name", "colour", "share"}] of the formations under a (Multi)Polygon in lon/lat, largest first
    (shares of the outline's area; what the map doesn't cover isn't counted), or None when the pack has none there"""
    import math
    import shapely
    import shapely.errors
    found_index = _index()
    if found_index is None:
        return None
    path, stamp, boxes = found_index
    outline = shapely.make_valid(outline)  # a drawn or published outline crossing itself (a bow tie)
    w, s_, e, n = outline.bounds
    # areas in degrees² are fine for shares within one small outline once longitudes are scaled to latitude's
    k = math.cos(math.radians(outline.centroid.y))
    total = outline.area * k
    found = {}
    for g, (bw, bs, be, bn) in enumerate(boxes):
        if bw > e or be < w or bs > n or bn < s_:
            continue
        geoms, rows = _group(path, stamp, g)
        for i in shapely.STRtree(geoms).query(outline, predicate="intersects"):
            try:
                part = shapely.intersection(geoms[i], outline).area * k
            except shapely.errors.GEOSException:  # an invalid piece of the map (the BRGM's own): repaired first
                part = shapely.intersection(shapely.make_valid(geoms[i]), outline).area * k
            notation, descr, colour = rows[i]
            key = (notation, descr)
            found[key] = (found.get(key, (0, colour))[0] + part, colour)
    if not found:
        return None
    units = [{"notation": n or None, "name": d, "colour": c, "share": round(a / total, 3)}
             for (n, d), (a, c) in found.items() if a / total >= MIN_SHARE]
    return sorted(units, key=lambda u: -u["share"]) or None


def macrostrat(lat, lng):
    """{"units": [{"name", "lithology", "age", "colour", "share": 1}], "scale"} from Macrostrat's most detailed map at
    a point, or None where it has none. Raises OSError when it can't be reached."""
    req = Request(MACROSTRAT.format(lat=lat, lng=lng), headers={"User-Agent": "WineLib"})
    with urlopen(req, timeout=20) as r:
        data = json.load(r).get("success", {}).get("data") or []
    order = ["large", "medium", "small", "tiny"]
    data = sorted((u for u in data if u.get("scale") in order), key=lambda u: order.index(u["scale"]))
    if not data:
        return None
    u = data[0]
    top, bottom = u.get("t_int_name"), u.get("b_int_name")
    age = top if top == bottom or not bottom else f"{bottom} to {top}"
    return {"units": [{"notation": None, "name": u.get("name") or u.get("lith"), "lithology": u.get("lith"),
                       "age": age, "colour": u.get("color"), "share": 1}],
            "scale": SCALES.get(u["scale"])}
