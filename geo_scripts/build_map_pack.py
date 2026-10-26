"""The map data pack: the outlines others may have, from your shape store (data/geo/shapes/, build_shapes.py), as one
zip a new installation downloads (Settings › Maintenance › Map outlines). Only sources whose licence allows it, each
with its credit; the vineyards only INAO's premier crus (Weinlagen-info's are scraped: they stay yours).

    python geo_scripts/build_map_pack.py                 # -> dist/winelib-map-pack.zip
    gh release upload map-pack dist/winelib-map-pack.zip --clobber      # publish (a release tagged map-pack)

The zip: shapes/<source>.parquet as the store has them (filtered, and without the full-detail `geometry` column the
app never reads: only the display outline), shapes/manifest.json, pack.json (what's in it,
licences) and CREDITS.md.
"""
import argparse
import hashlib
import json
import os
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# The sources that ship: licence, credit, where they come from; "only": the source_id prefix of the rows that ship
PACK = {
    "inao": {"licence": "Licence Ouverte 2.0 (Etalab)", "credit": "INAO, Délimitation parcellaire des AOC viticoles",
             "url": "https://www.data.gouv.fr"},
    "inao_denom": {"licence": "Licence Ouverte 2.0 (Etalab)", "credit": "INAO, aires géographiques des SIQO",
                   "url": "https://www.data.gouv.fr"},
    "inao_aires": {"licence": "Licence Ouverte 2.0 (Etalab)", "credit": "INAO, aires géographiques des SIQO",
                   "url": "https://www.data.gouv.fr"},
    "eu": {"licence": "CC0 1.0", "credit": "Candiago et al. (2022), A geospatial inventory of regulatory information "
                                           "for wine protected designations of origin in Europe, Scientific Data",
           "url": "https://doi.org/10.6084/m9.figshare.c.5877659"},
    "ava": {"licence": "CC0 1.0", "credit": "UC Davis Library, American Viticultural Areas project",
            "url": "https://github.com/UCDavisLibrary/ava"},
    "au": {"licence": "CC BY 4.0", "credit": "Wine Australia, Wine Geographical Indications Australia",
           "url": "https://wineaustralia-opendata-wineaustralia.hub.arcgis.com/datasets/2dd4c385f0ed4d109c2e18ae99e819e2"},
    "admin": {"licence": "Public domain", "credit": "Natural Earth", "url": "https://www.naturalearthdata.com/"},
    "vineyard": {"licence": "Licence Ouverte 2.0 (Etalab)", "credit": "INAO, premiers crus (délimitation parcellaire)",
                 "url": "https://www.data.gouv.fr",
                 "only": "inao-pc:"},
}
FORMAT, VERSION = "winelib-map-pack", 1


def pack_source(store_dir, out_dir, name, spec):
    """Copies one store file into the pack (its rows filtered by `only`). (rows, size) or None when absent."""
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    src = os.path.join(store_dir, f"{name}.parquet")
    if not os.path.exists(src):
        return None
    table = pq.read_table(src)
    if spec.get("only"):
        table = table.filter(pc.starts_with(table["source_id"], spec["only"]))
    # Only the display outline: the app never reads the full-detail one (most of the file's size)
    meta = json.loads((table.schema.metadata or {}).get(b"geo", b"{}"))
    meta.get("columns", {}).pop("geometry", None)
    meta["primary_column"] = "display"
    table = table.drop_columns([c for c in ("geometry",) if c in table.column_names])
    table = table.replace_schema_metadata({b"geo": json.dumps(meta).encode()})
    dst = os.path.join(out_dir, f"{name}.parquet")
    pq.write_table(table, dst, compression="zstd")
    return table.num_rows, os.path.getsize(dst)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build(geo_dir, out_zip, log=print):
    store_dir = os.path.join(geo_dir, "shapes")
    try:
        with open(os.path.join(store_dir, "manifest.json")) as f:
            manifest = json.load(f)
    except (OSError, ValueError):
        raise SystemExit(f"No shape store in {store_dir}: run build_shapes.py first")
    work = out_zip + ".d"
    shapes = os.path.join(work, "shapes")
    os.makedirs(shapes, exist_ok=True)
    built = time.strftime("%Y-%m-%d")
    pack = {"format": FORMAT, "version": VERSION, "built": built, "sources": {}}
    new_manifest = {}
    for name, spec in PACK.items():
        done = pack_source(store_dir, shapes, name, spec)
        if done is None:
            log(f"{name}: not in the store, left out")
            continue
        rows, size = done
        meta = {k: spec[k] for k in ("licence", "credit", "url")}
        pack["sources"][name] = {"file": f"shapes/{name}.parquet", "rows": rows, "size": size,
                                 "sha256": sha256(os.path.join(shapes, f"{name}.parquet")), **meta}
        new_manifest[name] = {"file": f"{name}.parquet", "rows": rows, "built": (manifest.get(name) or {}).get("built"),
                              "link": (manifest.get(name) or {}).get("link"), "pack": built, **meta}
        log(f"{name}: {rows} shapes, {size / 1e6:.1f} MB ({spec['licence']})")
    with open(os.path.join(shapes, "manifest.json"), "w") as f:
        json.dump(new_manifest, f, indent=2, sort_keys=True)
    with open(os.path.join(work, "pack.json"), "w") as f:
        json.dump(pack, f, indent=2)
    with open(os.path.join(work, "CREDITS.md"), "w", encoding="utf-8") as f:
        f.write(f"# WineLib map outlines ({built})\n\n")
        for name, s in pack["sources"].items():
            f.write(f"- **{name}**: {s['credit']}. {s['licence']}. {s['url']}\n")
    os.makedirs(os.path.dirname(os.path.abspath(out_zip)), exist_ok=True)
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_STORED) as z:  # parquet files are compressed already
        for folder, _, files in os.walk(work):
            for fn in files:
                path = os.path.join(folder, fn)
                z.write(path, os.path.relpath(path, work))
    for folder, _, files in os.walk(work, topdown=False):
        for fn in files:
            os.remove(os.path.join(folder, fn))
        os.rmdir(folder)
    log(f"{out_zip}: {os.path.getsize(out_zip) / 1e6:.1f} MB")
    return pack


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--geo-dir", default=os.getenv("GEO_DIR") or os.path.join(ROOT, "data", "geo"))
    parser.add_argument("--out", default=os.path.join(ROOT, "dist", "winelib-map-pack.zip"))
    args = parser.parse_args()
    build(args.geo_dir, args.out)
