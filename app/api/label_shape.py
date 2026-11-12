"""The outline drawn on a wine's label (its wine page): its appellation's shape, else its region's, as an SVG path
in a 100x100 box, simplified to a few dozen points (a label's emblem, not a map)."""
import json
import math

import geo

BOX = 100
PAD = 4


def _path(geojson):
    """An SVG path (d) of a GeoJSON polygon or multipolygon, fitted into the box (north up, longitudes shrunk by the
    latitude's cosine so the shape keeps its proportions); None when there's nothing to draw."""
    import shapely
    g = shapely.from_geojson(geojson if isinstance(geojson, str) else json.dumps(geojson))
    if g.is_empty:
        return None
    x0, y0, x1, y1 = g.bounds
    k = math.cos(math.radians((y0 + y1) / 2))
    w, h = (x1 - x0) * k, y1 - y0
    if w <= 0 or h <= 0:
        return None
    # simplified to about 1% of its size: dozens of points, not thousands
    g = shapely.simplify(g, max(x1 - x0, y1 - y0) / 120, preserve_topology=True)
    scale = (BOX - 2 * PAD) / max(w, h)
    ox, oy = (BOX - w * scale) / 2, (BOX - h * scale) / 2
    parts = []
    polys = getattr(g, "geoms", [g])
    # the small islands of a big shape dropped (a speck on a label)
    biggest = max(p.area for p in polys if p.geom_type == "Polygon") if polys else 0
    for p in polys:
        if p.geom_type != "Polygon" or p.area < biggest * 0.01:
            continue
        for ring in [p.exterior, *p.interiors]:
            pts = [(ox + (x - x0) * k * scale, oy + (y1 - y) * scale) for x, y in ring.coords[:-1]]
            if len(pts) >= 3:
                parts.append("M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + "Z")
    return "".join(parts) or None


def of_wine(w):
    """{"d", "of"} of the wine's label outline (of: "appellation" or "region"), or None."""
    try:
        if w.appellation is not None:
            text, _ = geo.shape("appellation", w.appellation)
            if text and (d := _path(text)):
                return {"d": d, "of": "appellation"}
        if w.region_obj is not None:
            text, _ = geo.region_outline(w.region_obj.name)
            if text and (d := _path(text)):
                return {"d": d, "of": "region"}
    except Exception:  # a broken shape: the label shows the producer's initials
        return None
    return None
