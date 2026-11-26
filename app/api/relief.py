"""A vineyard's relief: its elevation, slope and aspect, worked out from its outline over Mapterhorn's open terrain
tiles (mapterhorn.com: Terrarium-encoded WebP, 512 px; IGN's RGE ALTI and LiDAR HD in France, 5 m to 0.5 m, 30 m
worldwide; each source's own open licence, listed at mapterhorn.com/attribution).

The outline's pixels at the finest zoom that keeps it to a few tiles (z15, about 1.6 m a pixel in Burgundy), the
elevation smoothed over ~10 m (the vine rows and terraces of a 0.5 m model aren't the hillside's slope), then:
- elevation: lowest and highest (the 1st and 99th percentiles: a stray pixel isn't the vineyard) and the mean;
- slope: the median and the steepest tenth (90th percentile), in degrees;
- aspect: where the hillside faces, the slope-weighted mean of the downhill directions (0 north, 90 east), None
  when it's flat (median slope under 2 degrees) or faces every way (the directions cancel out);
- contour lines inside the outline, a handful (the interval from its elevation range), and the outline cut into
  bands of height (its shading from the bottom of the slope to the top), for the maps.
"""
import io
import json
import math
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError
from urllib.request import Request, urlopen

TILES = "https://tiles.mapterhorn.com/{z}/{x}/{y}.webp"
SIZE = 512
MAX_ZOOM = 15
MIN_ZOOM = 8
MAX_TILES = 9
SMOOTH_M = 10
FLAT_DEG = 2
EARTH = 40075016.686  # the equator, in metres
POINTS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]


def compass(deg):
    """16 points: 112 -> "ESE" """
    return POINTS[round(deg / 22.5) % 16]


def pixel_m(z, lat):
    """The ground size of a tile pixel at zoom z and latitude lat, in metres"""
    return EARTH * math.cos(math.radians(lat)) / (2 ** z * SIZE)


def _world(lon, lat, z):
    """lon/lat -> the global pixel position at zoom z (Web Mercator)"""
    n = 2 ** z * SIZE
    x = (lon + 180) / 360 * n
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    return x, y


def tiles_for(bounds, z):
    """(x0, y0, x1, y1): the tiles covering bounds (west, south, east, north) at zoom z"""
    w, s, e, n = bounds
    x0, y0 = _world(w, n, z)
    x1, y1 = _world(e, s, z)
    return int(x0 // SIZE), int(y0 // SIZE), int(x1 // SIZE), int(y1 // SIZE)


def zoom_for(bounds):
    """The finest zoom (MAX_ZOOM at most) at which the outline takes MAX_TILES tiles or fewer"""
    for z in range(MAX_ZOOM, MIN_ZOOM - 1, -1):
        x0, y0, x1, y1 = tiles_for(bounds, z)
        if (x1 - x0 + 1) * (y1 - y0 + 1) <= MAX_TILES:
            return z
    return None


def decode(data):
    """A Terrarium tile (WebP or PNG bytes) -> elevations in metres (float32, SIZE x SIZE)"""
    import numpy as np
    from PIL import Image
    a = np.asarray(Image.open(io.BytesIO(data)).convert("RGB")).astype(np.float32)
    return a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768


def fetch(z, x, y):
    """One tile's elevations from Mapterhorn"""
    from tasks import USER_AGENT
    req = Request(TILES.format(z=z, x=x, y=y), headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=20) as r:
        tile = decode(r.read())
    if tile.shape != (SIZE, SIZE):  # not a terrain tile (an error page as an image): no relief from it
        raise ValueError(f"a {tile.shape[1]}x{tile.shape[0]} tile, not {SIZE}x{SIZE}")
    return tile


def _smooth(a, r):
    """a box mean over (2r+1)^2 pixels, edges padded"""
    import numpy as np
    if r < 1:
        return a
    p = np.pad(a, r, mode="edge").astype(np.float64)
    c = np.pad(np.cumsum(np.cumsum(p, axis=0), axis=1), ((1, 0), (1, 0)))
    k = 2 * r + 1
    s = c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]
    return (s / (k * k)).astype(np.float32)


INTERVALS = [1, 2, 5, 10, 20, 25, 50, 100]  # metres between contour lines: the smallest giving at most MAX_LINES
MAX_LINES = 8
CONTOUR_SIMPLIFY_M = 2


def interval_for(low, high):
    """The contour interval for an elevation range: a handful of lines over the vineyard, never a crowd"""
    return next((i for i in INTERVALS if (high - low) / i <= MAX_LINES), INTERVALS[-1])


def _segments(z, level, xs, ys):
    """Marching squares: the [(x1, y1, x2, y2)] pieces of the `level` contour across a grid z (rows from north to
    south), with each column's x and each row's y; crossings placed linearly along the cell edges"""
    import numpy as np
    a, b, c, d = z[:-1, :-1], z[:-1, 1:], z[1:, 1:], z[1:, :-1]  # a cell's corners: top left, top right, ...
    above = [v >= level for v in (a, b, c, d)]
    x0, x1 = xs[:-1][None, :], xs[1:][None, :]
    y0, y1 = ys[:-1][:, None], ys[1:][:, None]

    def at(v1, v2):  # where along an edge, 0 to 1
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.clip(np.nan_to_num((level - v1) / (v2 - v1), nan=0.5), 0, 1)
    # each edge: crossed?, the crossing's x and y
    edges = [
        (above[0] != above[1], x0 + (x1 - x0) * at(a, b), np.broadcast_to(y0, a.shape)),  # top
        (above[1] != above[2], np.broadcast_to(x1, a.shape), y0 + (y1 - y0) * at(b, c)),  # right
        (above[3] != above[2], x0 + (x1 - x0) * at(d, c), np.broadcast_to(y1, a.shape)),  # bottom
        (above[0] != above[3], np.broadcast_to(x0, a.shape), y0 + (y1 - y0) * at(a, d)),  # left
    ]
    crossed = np.stack([e[0] for e in edges])
    count = crossed.sum(axis=0)
    out = []
    # two crossings: one piece between them; four (a saddle): top with left, right with bottom
    for i, j in [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]:
        m = (count == 2) & crossed[i] & crossed[j]
        if m.any():
            out.append(np.stack([edges[i][1][m], edges[i][2][m], edges[j][1][m], edges[j][2][m]], axis=1))
    m = count == 4
    for i, j in [(0, 3), (1, 2)]:
        if m.any():
            out.append(np.stack([edges[i][1][m], edges[i][2][m], edges[j][1][m], edges[j][2][m]], axis=1))
    return np.concatenate(out) if out else np.empty((0, 4))


BANDS = 10  # the shading from the bottom of the slope to the top: about this many bands


def _levels(low, high, step):
    import numpy as np
    return np.arange(math.ceil(low / step) * step, high + 0.01, step)


def contours(geom, smooth, px, py, low, high):
    """{"lines": [{"ele", "line": GeoJSON}] the contour lines inside a vineyard's outline (interval_for its range),
    "bands": [{"ele", "t", "area": GeoJSON}] its outline cut by finer contours (about BANDS of them), each with its
    height in the vineyard from 0 (the bottom) to 1 (the top), for the maps' shading}; simplified to a couple of
    metres. Both from its smoothed elevations."""
    import numpy as np
    import shapely
    from shapely.ops import linemerge
    # the grid cut to the outline (and a pixel around it): a vineyard is a few hundred pixels, not three tiles
    w, s, e, n = geom.bounds
    cols = np.where((px >= w) & (px <= e))[0]
    rows = np.where((py >= s) & (py <= n))[0]
    if len(cols) < 2 or len(rows) < 2 or high - low < 0.5:
        return {"lines": [], "bands": []}
    c0, c1 = max(cols[0] - 1, 0), min(cols[-1] + 2, len(px))
    r0, r1 = max(rows[0] - 1, 0), min(rows[-1] + 2, len(py))
    z, xs, ys = smooth[r0:r1, c0:c1], px[c0:c1], py[r0:r1]
    tolerance = CONTOUR_SIMPLIFY_M / (111_320 * math.cos(math.radians(geom.centroid.y)))

    def traced(level):
        seg = _segments(z, level, xs, ys)
        if not len(seg):
            return None
        return linemerge(shapely.MultiLineString([[(x1, y1), (x2, y2)] for x1, y1, x2, y2 in seg])).simplify(tolerance)

    lines = []
    for level in _levels(low, high, interval_for(low, high)):
        line = traced(level)
        inside = shapely.set_precision(shapely.intersection(line, geom), 1e-6) if line is not None else None
        if inside is not None and not inside.is_empty and inside.length > 0:
            lines.append({"ele": int(level), "line": json.loads(shapely.to_geojson(inside))})
    # bands: the outline cut along finer contours, each piece's height read at a point inside it
    step = (high - low) / BANDS
    cuts = [c for level in _levels(low + step / 2, high, step) if (c := traced(level)) is not None]
    pieces = shapely.get_parts(shapely.polygonize([shapely.union_all([geom.boundary, *cuts])]).geoms) if cuts else [geom]
    bands = []
    for piece in pieces:
        p = piece.representative_point()
        if not geom.contains(p):
            continue
        part = shapely.set_precision(shapely.intersection(piece, geom), 1e-6)
        if part.is_empty or part.area == 0:
            continue
        ci = int(np.clip(np.searchsorted(xs, p.x), 0, len(xs) - 1))
        ri = int(np.clip(np.searchsorted(-ys, -p.y), 0, len(ys) - 1))
        ele = float(z[ri, ci])
        bands.append({"ele": round(ele), "t": round(min(max((ele - low) / (high - low), 0), 1), 2),
                      "area": json.loads(shapely.to_geojson(part))})
    return {"lines": lines, "bands": bands}


def compute(geom, get=None):
    """{"elevation": {"min", "mean", "max"}, "slope": {"median", "steep"}, "aspect": degrees or None, "zoom"} for a
    shapely (Multi)Polygon in lon/lat; None when it's too big or no pixel falls inside. `get(z, x, y)` gives a
    tile's elevations (the tests' made-up ones)."""
    import numpy as np
    import shapely
    import geo
    get = get or fetch
    geom = geo.polygonal(geom)  # an outline crossing itself, or with a spike: repaired (geo.outline already does)
    if geom is None:
        return None
    top = zoom_for(geom.bounds)
    if top is None:
        return None
    # The finest zoom there is there: Mapterhorn's fine tiles cover France and some other places; elsewhere its 30 m
    # model stops lower (z14 in Piedmont), a missing tile a 404: a zoom lower then
    for z in range(top, MIN_ZOOM - 1, -1):
        x0, y0, x1, y1 = tiles_for(geom.bounds, z)
        keys = [(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)]
        try:
            with ThreadPoolExecutor(4) as pool:
                got = dict(zip(keys, pool.map(lambda k: get(z, *k), keys)))
            break
        except HTTPError as e:
            if e.code != 404 or z == MIN_ZOOM:
                raise
    grid = np.block([[got[(x, y)] for x in range(x0, x1 + 1)] for y in range(y0, y1 + 1)])
    # each pixel's centre in lon/lat
    n = 2 ** z * SIZE
    px = (np.arange(x0 * SIZE, (x1 + 1) * SIZE) + 0.5) / n * 360 - 180
    py = np.degrees(np.arctan(np.sinh(np.pi * (1 - 2 * (np.arange(y0 * SIZE, (y1 + 1) * SIZE) + 0.5) / n))))
    lon, lat = np.meshgrid(px, py)
    inside = shapely.contains_xy(geom, lon, lat)
    if inside.sum() < 4:
        return None
    m = pixel_m(z, geom.centroid.y)
    smooth = _smooth(grid, round(SMOOTH_M / m / 2))  # none where a pixel is already coarser than SMOOTH_M
    d_south, d_east = np.gradient(smooth, m)  # rows run south, columns east
    gx, gy = d_east[inside], d_south[inside]
    steepness = np.hypot(gx, gy)
    slope = np.degrees(np.arctan(steepness))
    elev = grid[inside]
    # downhill, summed: east is -d/deast, north is +d/dsouth (north is minus south)
    east, north = float(-gx.sum()), float(gy.sum())
    median = float(np.median(slope))
    together = math.hypot(east, north) / max(float(steepness.sum()), 1e-9)
    aspect = None if median < FLAT_DEG or together < 0.2 else round(math.degrees(math.atan2(east, north))) % 360
    low, high = round(float(np.percentile(elev, 1))), round(float(np.percentile(elev, 99)))
    return {"elevation": {"min": low, "mean": round(float(elev.mean())), "max": high},
            "slope": {"median": round(median, 1), "steep": round(float(np.percentile(slope, 90)), 1)},
            "aspect": aspect, "zoom": z,
            # between the same lowest and highest points as reported: a stray pixel spreads neither the lines nor the bands
            "contours": contours(geom, smooth, px, py, float(low), float(high))}
