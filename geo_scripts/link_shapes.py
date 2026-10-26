"""Shape links from a PC: each appellation and vineyard linked to its shape in the store (data/geo/shapes/, built by
build_shapes.py), the `boundary` column. The work is the app's (app/api/shape_links.py: link rules in
app/api/data/shape_sources.json), as Settings › Maintenance › Shape links; this prints its report.

    python geo_scripts/link_shapes.py              # dry run: what would be linked, and what can't be
    python geo_scripts/link_shapes.py --commit
    python geo_scripts/link_shapes.py --all        # list every row that can't be linked, not just examples

Rerun after build_shapes.py or after adding appellations / vineyards.
"""
import argparse
import os
import sys

from sqlalchemy import create_engine

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "app", "api"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shape_links import EXAMPLES, SOURCES_FILE, link  # noqa: E402  (the app's: app/api/shape_links.py)

def main(geo_dir, db_url, commit=False, show_all=False, sources_file=SOURCES_FILE):
    try:
        result = link(create_engine(db_url), geo_dir, commit, sources_file)
    except ValueError as e:
        sys.exit(str(e))
    print("Store: " + ", ".join(f"{s} {n}" for s, n in result["store"].items())
          + (f" (not built: {', '.join(result['absent'])})" if result["absent"] else ""))
    for table, t in result["tables"].items():
        missing, ambiguous, mismatched = t["missing"], t["ambiguous"], t["mismatched"]
        print(f"\n{table}: {t['rows']} rows" + (" (adds the boundary column)" if t["added"] else ""))
        for source, n in t["linked"].items():
            print(f"  linked to {source}: {n}")
        print(f"  no shape in the store for their id or name: {len(missing)}")
        print(f"  ambiguous (their id is in several files, none or several with their name): {len(ambiguous)}")
        print(f"  linked, but the shape has another name (check them): {len(mismatched)}")
        print(f"  nothing to link by (no id, not a linked country): {t['none']}")
        print(f"  changes: {len(t['changes'])}")
        if missing:
            print(f"  Without a shape{'' if show_all or len(missing) <= EXAMPLES else f' ({EXAMPLES} of {len(missing)}; --all for every one)'}:")
            for row, tried in (missing if show_all else missing[:EXAMPLES]):
                where = ", ".join(x for x in (row["region"], row["country"]) if x)
                print(f"    {row['name']} ({where}): no {' / '.join(tried)}")
        if ambiguous:
            print(f"  Ambiguous, not linked{'' if show_all or len(ambiguous) <= EXAMPLES else f' ({EXAMPLES} of {len(ambiguous)}; --all for every one)'}:")
            for row, options in (ambiguous if show_all else ambiguous[:EXAMPLES]):
                print(f"    {row['name']} ({row['region']}): {' or '.join(options)}")
        if mismatched:
            print(f"  Another name{'' if show_all or len(mismatched) <= EXAMPLES else f' ({EXAMPLES} of {len(mismatched)}; --all for every one)'}:")
            for row, found, shape_name in (mismatched if show_all else mismatched[:EXAMPLES]):
                print(f"    {row['name']} ({row['region']}) -> {found}, named {shape_name}")
    print("\n✓ Saved." if commit else "\nDry run: nothing saved. Run with --commit to save.")


if __name__ == "__main__":
    import config
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--commit", action="store_true", help="save (dry run by default)")
    parser.add_argument("--all", action="store_true", help="list every row without a shape")
    parser.add_argument("--geo-dir", default=os.getenv("GEO_DIR") or os.path.join(PROJECT_ROOT, "data", "geo"))
    parser.add_argument("--sources", default=SOURCES_FILE)
    args = parser.parse_args()
    main(args.geo_dir, os.getenv("DB_URL") or config.DB_URL, args.commit, args.all, args.sources)
