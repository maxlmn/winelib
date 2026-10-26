"""Coordinates from a Google Maps link, including the short share links (maps.app.goo.gl/...).

Short links carry no coordinates: they are followed (Google hosts only) to the full URL. When even that
has none (newer share links end at ?q=<name, address>&ftid=...), the page is searched for the place's own
pin, and failing that the address is looked up on OpenStreetMap (an approximate position).

Never the page's map centre or a bare @lat,lng viewport: for a request from the server, Google centres the
map on the server's own location, which is how links used to land on "current location".
"""
import json
import re
import urllib.error
import urllib.parse
import urllib.request

ALLOWED_HOST = re.compile(r"^(maps\.app\.goo\.gl|goo\.gl|((www|maps|consent)\.)?google\.[a-z]{2,3}(\.[a-z]{2})?)$")
NUM = r"(-?\d{1,3}(?:\.\d+)?)"
# Most precise first: the place's own pin (!3d!4d), then explicit queries, then the viewport centre (@)
URL_PATTERNS = [
    re.compile(rf"!3d{NUM}!4d{NUM}"),
    re.compile(rf"[?&](?:q|query|ll|center|destination)={NUM},\s*\+?{NUM}"),
    re.compile(rf"/(?:search|place|dir)/{NUM},\s*\+?{NUM}"),
]
# A viewport (@lat,lng) only counts in a URL that names a place or a search, not on a bare map
VIEWPORT = re.compile(rf"@{NUM},{NUM}")
NAMES_A_PLACE = re.compile(r"/maps/(?:place|search|dir)/|[?&](?:q|query)=")
# In the page: only the place's own pin (its data or the preview image's marker), never the map centre
PAGE_PATTERNS = [
    re.compile(rf"!3d{NUM}!4d{NUM}"),
    re.compile(rf"markers={NUM}(?:%2C|,){NUM}"),
]
GEOCODER = "https://nominatim.openstreetmap.org/search"
TIMEOUT = 6
MAX_PAGE = 2_000_000
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36",
           "Accept-Language": "en"}


class LinkError(ValueError):
    pass


def is_google(url):
    try:
        parts = urllib.parse.urlsplit(url.strip())
    except ValueError:
        return False
    return parts.scheme in ("http", "https") and bool(ALLOWED_HOST.match((parts.hostname or "").lower()))


def _valid(lat, lng):
    return abs(lat) <= 90 and abs(lng) <= 180 and (lat, lng) != (0, 0)


def find_coordinates(text, patterns=URL_PATTERNS):
    for p in patterns:
        for m in p.finditer(text):
            lat, lng = float(m.group(1)), float(m.group(2))
            if _valid(lat, lng):
                return lat, lng
    return None


def url_coordinates(url):
    """Coordinates a URL states: a pin or query, else its viewport when it names a place."""
    return find_coordinates(url) or (find_coordinates(url, [VIEWPORT]) if NAMES_A_PLACE.search(url) else None)


def place_query(url):
    """The full place text of /maps/place/<name, address>/ or ?q=<...>, for geocoding."""
    m = re.search(r"/maps/(?:place|search)/([^/@?]+)", url)
    text = m.group(1) if m else (urllib.parse.parse_qs(urllib.parse.urlsplit(url).query).get("q") or [""])[0]
    text = urllib.parse.unquote_plus(text).strip()
    return text if text and not find_coordinates(f"?q={text}") else None


def _geocode(query):
    """(lat, lng) of an address from OpenStreetMap's Nominatim, or None. Separate so tests can replace it."""
    url = f"{GEOCODER}?{urllib.parse.urlencode({'format': 'jsonv2', 'limit': 1, 'q': query})}"
    req = urllib.request.Request(url, headers={"User-Agent": "WineLib/1.0 (personal wine cellar app)", "Accept-Language": "en"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
        hits = json.load(res)
    return (float(hits[0]["lat"]), float(hits[0]["lon"])) if hits else None


def place_name(url):
    """The place's name from /maps/place/<name>/ or ?q=<name>, if it reads like one."""
    m = re.search(r"/maps/place/([^/@?]+)", url)
    name = m.group(1) if m else (urllib.parse.parse_qs(urllib.parse.urlsplit(url).query).get("q") or [""])[0]
    name = urllib.parse.unquote_plus(name).strip()
    if not name or find_coordinates(f"?q={name}"):
        return None
    return name.split(",")[0].strip() or None


class _GoogleOnly(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not is_google(newurl):
            raise LinkError("That link leads outside Google Maps")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _open(url):
    """(final URL, page text). Separate so tests can replace it."""
    opener = urllib.request.build_opener(_GoogleOnly)
    req = urllib.request.Request(url, headers=HEADERS)
    with opener.open(req, timeout=TIMEOUT) as res:
        return res.geturl(), res.read(MAX_PAGE).decode("utf-8", "replace")


def _expand(url):
    """The URL plus any URL wrapped in it (EU consent pages keep the real one in ?continue=)."""
    out = [url]
    for key, values in urllib.parse.parse_qs(urllib.parse.urlsplit(url).query).items():
        if key in ("continue", "link", "url"):
            out += values
    return [urllib.parse.unquote(u) for u in out]


def resolve(url):
    """{"lat", "lng", "name"} for a Google Maps link. Raises LinkError when it can't."""
    url = url.strip()
    if not is_google(url):
        raise LinkError("Not a Google Maps link")
    for u in _expand(url):
        if c := url_coordinates(u):
            return {"lat": c[0], "lng": c[1], "name": place_name(u)}
    try:
        final, page = _open(url)
    except LinkError:
        raise
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise LinkError(f"Couldn't open the link ({getattr(e, 'reason', e)})") from e
    name = next((n for u in _expand(final) if (n := place_name(u))), None)
    for u in _expand(final):
        if c := url_coordinates(u):
            return {"lat": c[0], "lng": c[1], "name": name or place_name(u)}
    if c := find_coordinates(page, PAGE_PATTERNS):
        return {"lat": c[0], "lng": c[1], "name": name}
    query = next((q for u in _expand(final) if (q := place_query(u))), None)
    if query:
        try:
            c = _geocode(query)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError):
            c = None
        if c:
            return {"lat": c[0], "lng": c[1], "name": name, "approximate": True}
    raise LinkError("No coordinates behind that link: open it in Google Maps and paste the coordinates instead")
