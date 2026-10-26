"""Place coordinates from OpenStreetMap (Nominatim): free, no key. Its usage policy asks for an identifying
User-Agent and at most one request per second, so batches pause between places.

Used by the place form's "Search OpenStreetMap" and Settings › Maintenance › Place coordinates.
"""
import json
import time
import urllib.parse
import urllib.request

from winelib_utils import USER_AGENT

NOMINATIM = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": USER_AGENT, "Accept-Language": "en"}
TIMEOUT = 10
# What a restaurant, bar, shop or winery is filed under on OpenStreetMap: a batch only trusts these
POI_CATEGORIES = {"amenity", "tourism", "shop", "leisure", "craft", "building", "historic"}


def _get_json(url):
    """Separate so tests can replace it."""
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=TIMEOUT) as res:
        return json.load(res)


def search(query, limit=5):
    """[{"name", "address", "lat", "lng", "category", "type"}] for a free-text query, best first."""
    q = urllib.parse.urlencode({"format": "jsonv2", "limit": limit, "addressdetails": 0, "q": query})
    return [{"name": h.get("name") or h.get("display_name", "").split(",")[0],
             "address": h.get("display_name", ""),
             "lat": round(float(h["lat"]), 6), "lng": round(float(h["lon"]), 6),
             "category": h.get("category"), "type": h.get("type")}
            for h in _get_json(f"{NOMINATIM}?{q}")]


def place_query(place):
    return ", ".join(x for x in (place.name, place.city, place.country) if x)


def missing(session):
    """Places without coordinates (names starting with "@" are placeholders, not places)."""
    from winelib_utils.models import Place
    return (session.query(Place).filter(Place.lat.is_(None), ~Place.name.startswith("@"))
            .order_by(Place.name).all())


def fill_missing(session, limit=None, commit=False, log=print, pause=1.1):
    """Looks up places without coordinates and takes the best hit that is a place (a restaurant, a shop...,
    not a street or a town). Saves only with commit. [(place, hit or None)]."""
    places = missing(session)[:limit] if limit else missing(session)
    out = []
    for i, p in enumerate(places):
        if i:
            time.sleep(pause)
        hits = [h for h in search(place_query(p)) if h["category"] in POI_CATEGORIES]
        hit = hits[0] if hits else None
        if hit is None:
            log(f"–  {place_query(p)}: no match on OpenStreetMap")
        else:
            log(f"✅ {place_query(p)} → {hit['address'][:90]} ({hit['lat']}, {hit['lng']})")
            if commit:
                p.lat, p.lng = hit["lat"], hit["lng"]
        out.append((p, hit))
    if commit:
        session.commit()
    return out
