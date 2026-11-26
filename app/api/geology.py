"""A vineyard's geology: the rock formations under its outline and the share of each.

- In France, BRGM's 1:50,000 geological maps (vectorised and harmonised by departement; Licence Ouverte 2.0, credit
  "BRGM"), shipped in the map pack as shapes/geology.parquet: the formations around the wine lieux-dits
  (geo_scripts/etl_geology.py), each with its map notation ("j3a"), its description as published and its colour.
  Worked out on each request from the file (a few milliseconds).
- Elsewhere, Macrostrat's map at the outline's centre (macrostrat.org, CC BY 4.0): its most detailed map there, often
  regional (1:1,000,000 in Europe). Asked once, kept in `geologies` (routers/geology.py).
"""
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
_loaded = {"stamp": None, "tree": None, "rows": None, "geoms": None}


def _path():
    return os.path.join(geo.SHAPES_DIR, "geology.parquet")


def _formations():
    """(STRtree, [(notation, descr, colour)]) of the pack's formations, read again when the file changes; (None, [])
    without it"""
    import pyarrow.parquet as pq
    import shapely
    path = _path()
    try:
        stamp = os.stat(path).st_mtime_ns
    except OSError:
        return None, []
    with _lock:
        if _loaded["stamp"] != stamp:
            t = pq.read_table(path, columns=["notation", "descr", "colour", "display"])
            geoms = shapely.from_wkb(t.column("display").to_numpy(zero_copy_only=False))
            rows = list(zip(t.column("notation").to_pylist(), t.column("descr").to_pylist(),
                            t.column("colour").to_pylist()))
            _loaded.update(stamp=stamp, tree=shapely.STRtree(geoms), rows=rows, geoms=geoms)
        return _loaded["tree"], _loaded["rows"]


def brgm(outline):
    """[{"notation", "name", "colour", "share"}] of the formations under a (Multi)Polygon in lon/lat, largest first
    (shares of the outline's area; what the map doesn't cover isn't counted), or None when the pack has none there"""
    import math
    import shapely
    tree, rows = _formations()
    if tree is None:
        return None
    hits = tree.query(outline, predicate="intersects")
    if not len(hits):
        return None
    # areas in degrees² are fine for shares within one small outline once longitudes are scaled to latitude's
    k = math.cos(math.radians(outline.centroid.y))
    total = outline.area * k
    found = {}
    for i in hits:
        part = shapely.intersection(_loaded["geoms"][i], outline).area * k
        notation, descr, colour = rows[i]
        key = (notation, descr)
        found[key] = (found.get(key, (0, colour))[0] + part, colour)
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
