"""paths.py: a checkout keeps its layout (data/, backups/, plugins/ in it); WINELIB_DATA (or an installed package)
puts everything in one folder; one path set on its own wins."""
import json
import os
import subprocess
import sys

API_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(API_DIR))
KEYS = ["DATA_DIR", "DB_URL", "GEO_DIR", "PHOTOS_DIR", "CACHE_DIR", "BACKUP_DIR", "PLUGINS_DIR", "LWIN_DB"]


def paths_with(**env):
    clean = {k: v for k, v in os.environ.items() if k not in
             {"DB_URL", "GEO_DIR", "PHOTOS_DIR", "GEO_CACHE_DIR", "THUMBS_DIR", "BACKUP_DIR", "PLUGINS_DIR", "LWIN_DB",
              "WINELIB_DATA"}}
    out = subprocess.run([sys.executable, "-c", f"import json, paths; print(json.dumps({{k: getattr(paths, k) for k in {KEYS!r}}}))"],
                         cwd=API_DIR, env={**clean, **env}, capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def test_a_checkout_keeps_its_layout():
    p = paths_with()
    assert p["DATA_DIR"] == os.path.join(ROOT, "data") and p["DB_URL"].endswith(os.path.join("data", "winelib.db"))
    assert p["BACKUP_DIR"] == os.path.join(ROOT, "backups") and p["PLUGINS_DIR"] == os.path.join(ROOT, "plugins")
    assert p["CACHE_DIR"] == os.path.join(API_DIR, ".cache")


def test_one_data_folder(tmp_path):
    p = paths_with(WINELIB_DATA=str(tmp_path), GEO_DIR="/geo")
    assert all(p[k].startswith(str(tmp_path)) or p[k].endswith(str(tmp_path)) for k in ("DATA_DIR", "PHOTOS_DIR",
               "CACHE_DIR", "BACKUP_DIR", "PLUGINS_DIR", "LWIN_DB"))
    assert p["DB_URL"] == f"sqlite:///{tmp_path / 'winelib.db'}" and p["GEO_DIR"] == "/geo"  # set on its own: wins
