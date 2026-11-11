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


def test_a_secrets_file_in_the_data_folder_is_read(tmp_path):
    """Keys in .secrets.env reach the app (they were only read by a module nothing imported); the environment wins,
    and a line left empty isn't a setting."""
    (tmp_path / ".secrets.env").write_text('# keys\nESRI_API_KEY="from-file"\nWINELABS_API_KEY=file\nGEO_DIR=\n', encoding="utf-8")
    code = "import json, os, paths; print(json.dumps([os.getenv('ESRI_API_KEY'), os.getenv('WINELABS_API_KEY'), paths.GEO_DIR]))"
    clean = {k: v for k, v in os.environ.items() if k not in {"ESRI_API_KEY", "GEO_DIR", "DB_URL"}}
    out = subprocess.run([sys.executable, "-c", code], cwd=API_DIR, capture_output=True, text=True, check=True,
                         env={**clean, "WINELIB_DATA": str(tmp_path), "WINELABS_API_KEY": "env"}).stdout
    esri, winelabs, geo = json.loads(out)
    assert esri == "from-file" and winelabs == "env" and geo == os.path.join(str(tmp_path), "geo")
