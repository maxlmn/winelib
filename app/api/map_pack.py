"""The map data pack: the published outlines (the openly licensed sources, credited), downloaded into the shape store by
Settings › Maintenance › Map outlines. MAP_PACK_URL is where it is: an https address (a GitHub release's file), or a
local file. Each file is checked against the pack's checksums before it replaces the store's, and the store's
manifest keeps each source's licence and credit (listed in Settings).
"""
import hashlib
import json
import os
import shutil
import tempfile
import urllib.request
import zipfile

import geo

# The published pack (a release tagged map-pack on the public repository); MAP_PACK_URL for another address or a file
MAP_PACK_URL = os.getenv("MAP_PACK_URL", "https://github.com/maxlmn/winelib/releases/download/map-pack/winelib-map-pack.zip")
FORMAT = "winelib-map-pack"


def installed():
    """{source: manifest entry} of the shape store (rows, licence, credit when it came from a pack)."""
    try:
        with open(os.path.join(geo.SHAPES_DIR, "manifest.json")) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def fetch(url, log=print):
    """A local copy of the pack: (path, whether it's a temporary file to delete)."""
    if not url:
        raise RuntimeError("No map pack address: set MAP_PACK_URL (an https address or a file)")
    if url.startswith(("http://", "https://")):
        fd, path = tempfile.mkstemp(suffix=".zip")
        os.close(fd)
        log(f"Downloading {url}")
        with urllib.request.urlopen(url, timeout=60) as r, open(path, "wb") as f:
            shutil.copyfileobj(r, f, 1 << 20)
        return path, True
    path = url[len("file://"):] if url.startswith("file://") else url
    if not os.path.isfile(path):
        raise RuntimeError(f"No map pack at {path}")
    return path, False


def install(zip_path, log=print):
    """Puts the pack's outlines into the shape store: each file checked, then swapped in; the manifest updated for
    those sources (the others the store has stay). {source: rows}."""
    shapes = geo.SHAPES_DIR
    os.makedirs(shapes, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        pack = json.loads(z.read("pack.json"))
        if pack.get("format") != FORMAT:
            raise RuntimeError("Not a WineLib map pack (pack.json)")
        manifest = installed()
        new = json.loads(z.read("shapes/manifest.json"))
        done = {}
        for name, s in pack["sources"].items():
            if os.path.basename(s["file"]) != f"{name}.parquet":  # only <source>.parquet, in the store
                raise RuntimeError(f"Unexpected file in the pack: {s['file']}")
            tmp = os.path.join(shapes, f"{name}.parquet.part")
            h = hashlib.sha256()
            with z.open(s["file"]) as src, open(tmp, "wb") as dst:
                for chunk in iter(lambda: src.read(1 << 20), b""):
                    h.update(chunk)
                    dst.write(chunk)
            if h.hexdigest() != s["sha256"]:
                os.remove(tmp)
                raise RuntimeError(f"{name}: the file doesn't match the pack's checksum (a damaged download?)")
            os.replace(tmp, os.path.join(shapes, f"{name}.parquet"))
            manifest[name] = new.get(name) or {"file": f"{name}.parquet", "rows": s["rows"]}
            done[name] = s["rows"]
            log(f"{name}: {s['rows']} outlines ({s['licence']})")
    with open(os.path.join(shapes, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
    geo.reset()  # the map reads the new files
    return done


def credits():
    """[{source, rows, licence, credit, url}] of the installed sources that came with their credit."""
    return [{"source": name, "rows": m.get("rows"), "licence": m["licence"], "credit": m.get("credit"),
             "url": m.get("url")} for name, m in sorted(installed().items()) if m.get("licence")]
