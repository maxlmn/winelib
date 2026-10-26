"""Rebuilds a database from an export (Settings › Your data › Download as JSON): every table, ids kept, into a new
or empty database (SQLite or Postgres). To move to another machine, or from Postgres to SQLite and back.

    python scripts/restore_export.py winelib_export_2026-10-25.json                       # data/winelib.db
    python scripts/restore_export.py winelib_export_2026-10-25.json --to postgresql://...

The database gets the app's schema first (its migrations); a column the export has and the schema doesn't is left out,
one the schema has and the export doesn't gets its default. A database that has any row in these tables is refused.
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_TO = f"sqlite:///{os.path.join(ROOT, 'data', 'winelib.db')}"


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
    parser.add_argument("--to", default=os.getenv("DB_URL") or DEFAULT_TO, help="the database to rebuild")
    args = parser.parse_args()
    with open(args.export, encoding="utf-8") as f:
        export = json.load(f)
    os.environ["DB_URL"] = args.to
    sys.path.insert(0, os.path.join(ROOT, "app", "api"))
    import migrate
    from sqlalchemy import create_engine
    engine = create_engine(args.to)
    migrate.upgrade(engine)  # the schema (a new database also gets an empty app_settings table)
    counts = restore(engine, export)
    print(f"Restored into {engine.url.render_as_string(hide_password=True)} (exported {export.get('exported')}): "
          + ", ".join(f"{n} {t}" for t, n in counts.items() if n))


if __name__ == "__main__":
    main()
