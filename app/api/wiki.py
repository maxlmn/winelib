"""A short description and a photo for grape pages, from Wikipedia.

Looked up on first view (the server needs internet access) and cached for a month in the app's cache
directory, so a page only asks Wikipedia once. The grape's own article is preferred: "Chenin blanc" over
anything else called Chenin.
"""
import json
import logging
import os
import re
import sqlite3
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

log = logging.getLogger(__name__)

LANG = os.getenv("WIKI_LANG", "en")
TIMEOUT = 6
HEADERS = {"User-Agent": "WineLib/1.0 (personal wine cellar app)", "Accept": "application/json"}
# Bump to drop what's cached (v1 saved resized image links that don't load; v2 could hold a search hit
# about another region, e.g. Santa Barbara County for the Pacific Northwest)
CACHE_VERSION = 3
FOUND_TTL = 30 * 86400
MISSING_TTL = 3 * 86400  # not found: try again in a few days (a page may appear, or a fix to the titles below)

# A page counts only if it is about wine (Jura the mountains, Georgia the US state...)
WINE_WORDS = re.compile(r"\b(wine|wines|grape|grapes|vineyards?|viticultur\w*|appellation|vintners?)\b", re.I)


def _get_json(url):
    """Separate so tests can replace it. None on a 404."""
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
            return json.load(res)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def _summary(title):
    url = f"https://{LANG}.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title.replace(' ', '_'), safe='')}?redirect=true"
    data = _get_json(url)
    if not data or data.get("type") == "disambiguation" or not data.get("extract"):
        return None
    return data


def _search(query):
    params = urllib.parse.urlencode({"action": "query", "list": "search", "srsearch": query, "srlimit": 3,
                                     "srprop": "", "format": "json"})
    data = _get_json(f"https://{LANG}.wikipedia.org/w/api.php?{params}") or {}
    return [r["title"] for r in data.get("query", {}).get("search", [])]


def _candidates(kind, name):
    """(title, from_search) to try in order: titles we expect first, then a search."""
    titles = [f"{name} (grape)", name, name.capitalize()]
    query = f"{name} grape variety"
    seen = set()
    for t in titles:
        if t and t not in seen:
            seen.add(t)
            yield t, False
    yield from ((t, True) for t in _search(query) if t not in seen)


def _plain(text):
    return unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()


def _mentions(data, name):
    """A search hit must be about this name: a search also returns other articles that mention wine."""
    return _plain(name) in _plain(f"{data.get('title')} {data.get('description')} {data['extract']}")


def _lookup(kind, name):
    for title, from_search in _candidates(kind, name):
        data = _summary(title)
        if data and WINE_WORDS.search(data["extract"]) and (not from_search or _mentions(data, name)):
            thumb = (data.get("thumbnail") or {}).get("source")
            return {
                "title": data.get("title") or title,
                "description": data.get("description"),
                "extract": data["extract"],
                # As Wikipedia gives it: other widths aren't always generated (never wider than the original)
                "image": thumb,
                "image_full": (data.get("originalimage") or {}).get("source"),
                "url": (data.get("content_urls") or {}).get("desktop", {}).get("page")
                or f"https://{LANG}.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}",
            }
    return None


# --- Cache -----------------------------------------------------------------------------------------------

_lock = threading.Lock()
_conn = None


def _db():
    global _conn
    if _conn is None:
        import paths  # the app's cache directory
        _conn = False
        if paths.CACHE_DIR:
            try:
                os.makedirs(paths.CACHE_DIR, exist_ok=True)
                _conn = sqlite3.connect(os.path.join(paths.CACHE_DIR, "wiki.sqlite"), check_same_thread=False)
                _conn.execute("CREATE TABLE IF NOT EXISTS about (key TEXT PRIMARY KEY, expires REAL, data TEXT)")
            except (OSError, sqlite3.Error) as e:
                log.warning("Wikipedia cache disabled (%s)", e)
                _conn = False
    return _conn


def reset():
    """Forget the cache connection (tests point the cache directory elsewhere)."""
    global _conn
    with _lock:
        if _conn:
            _conn.close()
        _conn = None


def about(kind, name):
    """{"found": True, title, description, extract, image, image_full, url} or {"found": False}."""
    key = f"{CACHE_VERSION}|{LANG}|{kind}|{name.strip().lower()}"
    db = _db()
    if db:
        with _lock:
            row = db.execute("SELECT expires, data FROM about WHERE key = ?", (key,)).fetchone()
        if row and row[0] > time.time():
            return json.loads(row[1])
    try:
        found = _lookup(kind, name)
        result, ttl = ({"found": True, **found}, FOUND_TTL) if found else ({"found": False}, MISSING_TTL)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        log.info("Wikipedia lookup failed for %s %s: %s", kind, name, e)
        return {"found": False, "error": "Wikipedia couldn't be reached"}
    if db:
        with _lock:
            db.execute("INSERT OR REPLACE INTO about VALUES (?, ?, ?)", (key, time.time() + ttl, json.dumps(result)))
            db.commit()
    return result
