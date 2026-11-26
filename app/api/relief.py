"""A vineyard's relief: its elevation, slope and aspect, worked out from its outline over Mapterhorn's open terrain
tiles (mapterhorn.com: Terrarium-encoded WebP, 512 px; IGN's RGE ALTI and LiDAR HD in France, 5 m to 0.5 m, 30 m
worldwide; each source's own open licence, listed at mapterhorn.com/attribution).

The outline's pixels at the finest zoom that keeps it to a few tiles (z15, about 1.6 m a pixel in Burgundy), the
elevation smoothed over ~10 m (the vine rows and terraces of a 0.5 m model aren't the hillside's slope), then:
- elevation: lowest and highest (the 1st and 99th percentiles: a stray pixel isn't the vineyard) and the mean;
- slope: the median and the steepest tenth (90th percentile), in degrees;
- aspect: where the hillside faces, the slope-weighted mean of the downhill directions (0 north, 90 east), None
  when it's flat (median slope under 2 degrees) or faces every way (the directions cancel out).
"""
import io
import math
from concurrent.futures import ThreadPoolExecutor
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
    req = Request(TILES.format(z=z, x=x, y=y), headers={"User-Agent": "WineLib"})
    with urlopen(req, timeout=20) as r:
        return decode(r.read())


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


def compute(geom, get=None):
    """{"elevation": {"min", "mean", "max"}, "slope": {"median", "steep"}, "aspect": degrees or None, "zoom"} for a
    shapely (Multi)Polygon in lon/lat; None when it's too big or no pixel falls inside. `get(z, x, y)` gives a
    tile's elevations (the tests' made-up ones)."""
    import numpy as np
    import shapely
    get = get or fetch
    z = zoom_for(geom.bounds)
    if z is None:
        return None
    x0, y0, x1, y1 = tiles_for(geom.bounds, z)
    keys = [(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)]
    with ThreadPoolExecutor(4) as pool:
        got = dict(zip(keys, pool.map(lambda k: get(z, *k), keys)))
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
    smooth = _smooth(grid, max(1, round(SMOOTH_M / m / 2)))
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
    return {"elevation": {"min": round(float(np.percentile(elev, 1))), "mean": round(float(elev.mean())),
                          "max": round(float(np.percentile(elev, 99)))},
            "slope": {"median": round(median, 1), "steep": round(float(np.percentile(slope, 90)), 1)},
            "aspect": aspect, "zoom": z}
