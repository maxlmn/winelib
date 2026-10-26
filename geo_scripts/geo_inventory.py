"""What's in data/geo: every file (grouped by folder) as one of
- app: the shape store (shapes/), the only thing the app reads;
- input: a file build_shapes.py reads (its source in shape_sources.json);
- raw: a download one of the geo_scripts turns into an input (INAO shapefiles, the EU geopackage, Natural Earth);
- unknown: nothing reads it (left from before the shape store, an old download...): safe to delete once shapes/ is
  built, after a look.
Changes nothing.

    python geo_scripts/geo_inventory.py              # one line per folder / file at the top of data/geo
    python geo_scripts/geo_inventory.py --files      # every file
    python geo_scripts/geo_inventory.py --geo-dir /srv/winelib/data/geo
"""
import argparse
import fnmatch
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCES_FILE = os.path.join(HERE, "..", "app", "api", "data", "shape_sources.json")

# Downloads the scripts read (pattern on the path inside data/geo -> the script)
RAW = [
    ("*delim-parcellaire*", "etl_inao_fr.py, build_inao_areas.py (INAO parcels)"),
    ("inao_aires/*delim-aire-geographique*", "build_inao_areas.py (INAO geographic areas)"),
    ("EU_PDO.gpkg", "etl_gpkg_pdo.py (EU PDOs)"),
    ("PDO_EU_id.json", "etl_gpkg_pdo.py (EU PDO ids)"),
    ("*ne_10m_admin_1_states_provinces*", "build_admin_areas.py, build_region_outlines.py (Natural Earth)"),
    ("vineyard_index*", "vineyards/weinlagen_download.py (the Weinlagen index it scrapes from)"),
]
ORDER = {"app": 0, "input": 1, "raw": 2, "unknown": 3}


def size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


def classify(rel, sources):
    """(kind, what reads it) for a path inside data/geo."""
    if rel.startswith("shapes/"):
        return "app", "the app (shape store)"
    if rel == "sources.local.json":
        return "app", "this installation's own sources (build_shapes.py, shape links)"
    for s in sources:
        if any(fnmatch.fnmatch(rel, pattern) for pattern in s["files"]):
            return "input", f"build_shapes.py, source {s['name']}"
    for pattern, script in RAW:
        if fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(rel, pattern + "/*") or fnmatch.fnmatch(rel, pattern + ".*"):
            return "raw", script
    return "unknown", "nothing"


def inventory(geo_dir):
    sys.path.insert(0, os.path.join(HERE, "..", "app", "api"))
    from shape_links import load_sources
    sources = list(load_sources(SOURCES_FILE, geo_dir).values())
    files = []
    for root, dirs, names in os.walk(geo_dir):
        dirs.sort()
        for name in sorted(names):
            path = os.path.join(root, name)
            rel = os.path.relpath(path, geo_dir).replace(os.sep, "/")
            kind, reader = classify(rel, sources)
            files.append((rel, os.path.getsize(path), os.path.getmtime(path), kind, reader))
    return sources, files


def main():
    parser = argparse.ArgumentParser(description="What's in data/geo, and what reads it.")
    parser.add_argument("--geo-dir", default=os.getenv("GEO_DIR") or os.path.join(HERE, "..", "data", "geo"))
    parser.add_argument("--files", action="store_true", help="every file, not one line per top-level entry")
    args = parser.parse_args()
    geo_dir = os.path.abspath(args.geo_dir)
    if not os.path.isdir(geo_dir):
        raise SystemExit(f"No folder {geo_dir}")
    sources, files = inventory(geo_dir)

    # One line per top-level entry (a folder can mix kinds: each kind on its own line)
    groups = defaultdict(lambda: [0, 0, set()])
    for rel, n, _, kind, reader in files:
        key = rel if args.files else rel.split("/")[0] + ("/" if "/" in rel else "")
        g = groups[(key, kind)]
        g[0] += 1
        g[1] += n
        g[2].add(reader)
    print(f"{geo_dir}\n")
    for kind in sorted(ORDER, key=ORDER.get):
        rows = sorted((k, v) for (k, kd), v in groups.items() if kd == kind)
        if not rows:
            continue
        total = sum(v[1] for _, v in rows)
        print(f"== {kind} ({size(total)})")
        for key, (count, n, readers) in rows:
            files_ = f"{count} files" if count > 1 else ""
            print(f"  {key:<50} {files_:>10} {size(n):>9}   {'; '.join(sorted(readers))}")
        print()

    # Sources without files, and inputs changed since the store was built
    found = {s["name"] for s in sources for rel, *_ in files if any(fnmatch.fnmatch(rel, p) for p in s["files"])}
    missing = [s["name"] for s in sources if s["name"] not in found]
    if missing:
        print(f"Sources in shape_sources.json without files here: {', '.join(missing)}")
    manifest = os.path.join(geo_dir, "shapes", "manifest.json")
    if os.path.exists(manifest):
        built = os.path.getmtime(manifest)
        newer = [rel for rel, _, t, kind, _ in files if kind == "input" and t > built]
        if newer:
            print(f"Inputs newer than the shape store (run build_shapes.py): {', '.join(newer[:10])}"
                  + (f" and {len(newer) - 10} more" if len(newer) > 10 else ""))
    else:
        print("No shape store yet (shapes/manifest.json): run geo_scripts/build_shapes.py")
    unknown = sum(n for _, n, _, kind, _ in files if kind == "unknown")
    if unknown:
        print(f"Unknown: {size(unknown)} nothing reads (check, then delete)")


if __name__ == "__main__":
    main()
