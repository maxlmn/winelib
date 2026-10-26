"""Where the app keeps its files.

- Run from a checkout of the repository (a Docker container, a dev machine): as always, data/ (database, map
  shapes, photos, LWIN list), backups/ and plugins/ in the checkout, caches next to the code.
- Installed (a package, no checkout around it): everything in the user's data folder: ~/.local/share/winelib
  (Linux), ~/Library/Application Support/winelib (macOS), %APPDATA%\\winelib (Windows).
- WINELIB_DATA: that folder instead, either way.

Each path can still be set on its own (DB_URL, GEO_DIR, PHOTOS_DIR, GEO_CACHE_DIR, THUMBS_DIR, BACKUP_DIR,
PLUGINS_DIR, LWIN_DB), as a docker-compose file can. Reference data and the region outlines ship with the code.
"""
import os
import sys

API_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(API_DIR, "..", ".."))
FROM_SOURCE = os.path.isdir(os.path.join(ROOT_DIR, "winelib_utils")) and os.path.isdir(os.path.join(ROOT_DIR, "app"))


def user_data_dir(name="winelib"):
    if sys.platform == "win32":
        return os.path.join(os.getenv("APPDATA") or os.path.expanduser("~"), name)
    if sys.platform == "darwin":
        return os.path.join(os.path.expanduser("~"), "Library", "Application Support", name)
    return os.path.join(os.getenv("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share"), name)


CHOSEN = os.getenv("WINELIB_DATA")
IN_CHECKOUT = FROM_SOURCE and not CHOSEN  # today's layout
DATA_DIR = os.path.abspath(CHOSEN or (os.path.join(ROOT_DIR, "data") if FROM_SOURCE else user_data_dir()))
HOME = ROOT_DIR if IN_CHECKOUT else DATA_DIR  # where backups/ and plugins/ are


def _path(env, *default):
    return os.getenv(env) or os.path.join(*default)


DB_URL = os.getenv("DB_URL") or f"sqlite:///{os.path.join(DATA_DIR, 'winelib.db')}"
GEO_DIR = _path("GEO_DIR", DATA_DIR, "geo")
PHOTOS_DIR = _path("PHOTOS_DIR", DATA_DIR, "images")
CACHE_DIR = _path("GEO_CACHE_DIR", API_DIR if IN_CHECKOUT else DATA_DIR, ".cache" if IN_CHECKOUT else "cache")
THUMBS_DIR = _path("THUMBS_DIR", CACHE_DIR, "thumbs")
BACKUP_DIR = _path("BACKUP_DIR", HOME, "backups")
PLUGINS_DIR = _path("PLUGINS_DIR", HOME, "plugins")
LWIN_DB = _path("LWIN_DB", DATA_DIR, "lwin", "lwin.sqlite")
REFERENCE_DIR = _path("REFERENCE_DIR", API_DIR, "data", "reference")

os.environ.setdefault("LWIN_DB", LWIN_DB)  # winelib_utils/match_lwin.py reads it
if DB_URL.startswith("sqlite"):
    os.makedirs(DATA_DIR, exist_ok=True)  # a new installation: the database's folder
