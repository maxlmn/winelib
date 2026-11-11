"""Rebuilds a database from an export (Settings › Your data › Download as JSON): every table, ids kept, into a new
or empty database (SQLite or Postgres). To move to another machine, or from Postgres to SQLite and back.

    python scripts/restore_export.py winelib_export_2026-10-25.json                       # the app's own database
    python scripts/restore_export.py winelib_export_2026-10-25.json --to postgresql://...
    python scripts/restore_export.py winelib_export_2026-10-25.json --photos winelib_photos_2026-10-25.zip

In Docker: docker compose cp the files into the container, then
    docker compose exec winelib python /app/scripts/restore_export.py /data/winelib_export_2026-10-25.json

--photos: the photos' zip (Settings › Your data, or a backup's photos_*.zip), put back in the photos folder; a
photo already there is kept.

The database gets the app's schema first (its migrations); a column the export has and the schema doesn't is left out,
one the schema has and the export doesn't gets its default. A database that has any row in these tables is refused.
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app", "api"))


def restore_photos(archive, photos_dir):
    """The zip's photos into photos_dir (flat names only; one already there is kept). How many were added."""
    import zipfile
    os.makedirs(photos_dir, exist_ok=True)
    added = 0
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            name = os.path.basename(info.filename)
            if info.is_dir() or not name or name != info.filename or name.startswith("."):
                continue  # no folders, no paths: the photos folder is flat
            target = os.path.join(photos_dir, name)
            if os.path.exists(target):
                continue
            with z.open(info) as src, open(target, "wb") as out:
                out.write(src.read())
            added += 1
    return added


def restore(engine, export):
    """Inserts the export's tables into the (migrated, empty) database. {table: rows}."""
    from datetime import date, datetime

    from sqlalchemy import Date, DateTime, MetaData, func, insert, select, text
    if export.get("format") != "winelib":
        raise SystemExit("Not a WineLib export (no \"format\": \"winelib\")")
    meta = MetaData()
    meta.reflect(engine)
    order = [t for t in meta.sorted_tables if t.name in export["tables"]]
    counts = {}
    with engine.begin() as conn:
        for t in order:
            if conn.execute(select(func.count()).select_from(t)).scalar():
                raise SystemExit(f"The database already has rows in {t.name}: restore into a new or empty one")
        for t in order:
            cols = {c.name: c for c in t.columns}
            rows = []
            for r in export["tables"][t.name]:
                row = {}
                for k, v in r.items():
                    if k not in cols:
                        continue
                    if isinstance(v, str) and isinstance(cols[k].type, DateTime):
                        v = datetime.fromisoformat(v)
                    elif isinstance(v, str) and isinstance(cols[k].type, Date):
                        v = date.fromisoformat(v[:10])
                    row[k] = v
                rows.append(row)
            if rows:
                conn.execute(insert(t), rows)
            counts[t.name] = len(rows)
        if conn.dialect.name == "postgresql":  # the next ids follow the restored ones
            for t in order:
                if "id" in t.columns and t.columns["id"].autoincrement:
                    conn.execute(text(f"SELECT setval(pg_get_serial_sequence('{t.name}', 'id'), "
                                      f"COALESCE((SELECT MAX(id) FROM {t.name}), 0) + 1, false)"))
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("export", help="the .json file")
    parser.add_argument("--to", help="the database to rebuild (default: the app's own: DB_URL, else its SQLite file)")
    parser.add_argument("--photos", help="the photos' zip, to put back too")
    args = parser.parse_args()
    with open(args.export, encoding="utf-8") as f:
        export = json.load(f)
    if args.to:
        os.environ["DB_URL"] = args.to
    import paths  # where the app keeps its files (WINELIB_DATA, .secrets.env), as the app itself reads them
    args.to = args.to or paths.DB_URL
    import migrate
    from sqlalchemy import create_engine
    engine = create_engine(args.to)
    migrate.upgrade(engine)  # the schema (a new database also gets an empty app_settings table)
    counts = restore(engine, export)
    print(f"Restored into {engine.url.render_as_string(hide_password=True)} (exported {export.get('exported')}): "
          + ", ".join(f"{n} {t}" for t, n in counts.items() if n))
    if args.photos:
        print(f"{restore_photos(args.photos, paths.PHOTOS_DIR)} photos put back in {paths.PHOTOS_DIR}")


if __name__ == "__main__":
    main()
