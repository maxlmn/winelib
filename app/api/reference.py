"""Reference data: regions, appellations, grapes, vineyards and producers, from app/api/data/reference/*.csv (shipped with the
code; how they were built: data/docs/how-built.md). At startup, after the migrations:

- a database without any region is given the lot (seed);
- every database then gets what a newer version ships (update), row by row by a stable key (a region's, grape's or
  producer's name, an appellation's name and country, a vineyard's outline link else its name and region): a row whose key it
  never received is added; a row it has gets its empty fields filled, never one overwritten. The keys received are
  kept (reference_keys), so a row deleted or renamed here doesn't come back. A database from before this has its
  current keys recorded the first time, changing nothing.

    python reference.py            # seed (an empty database) and update the database (paths.DB_URL)
    python reference.py --dry-run  # what an update would add and fill
"""
import csv
import logging
import os
import re
import sys
import unicodedata
from datetime import datetime

from sqlalchemy import Date, Float, Integer, func, insert, select, text, update as sql_update

import paths
from db import Appellation, Producer, ReferenceKey, Region, Varietal, Vineyard

log = logging.getLogger(__name__)
REFERENCE_DIR = paths.REFERENCE_DIR
# In this order (appellations and vineyards point at regions)
TABLES = [("regions.csv", Region), ("appellations.csv", Appellation), ("varietals.csv", Varietal),
          ("vineyards.csv", Vineyard), ("producers.csv", Producer)]
# Never reference data, whatever a file holds: a producer's notes, lists and importers are yours, its description and
# profile link copied text (the export that made these files leaves them out too)
PRIVATE = {"producers": {"notes", "lists", "importers", "description", "profile_url", "website"}}


def _value(value, column):
    """A CSV cell as the column's type (None when empty or unreadable)."""
    if value is None or value == "":
        return None
    try:
        if isinstance(column.type, Integer):
            return int(float(value))  # "80.0" from a spreadsheet
        if isinstance(column.type, Float):
            return float(value)
        if isinstance(column.type, Date):
            return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None
    return value


def rows(filename, model):
    """The CSV's rows as {column: value} for the model's columns (others ignored). A link to an outline drawn in
    the app (custom:<id>) isn't reference data: dropped."""
    path = os.path.join(REFERENCE_DIR, filename)
    if not os.path.exists(path):
        return []
    columns = {c.name: c for c in model.__table__.columns if c.name not in PRIVATE.get(model.__tablename__, ())}
    with open(path, encoding="utf-8-sig", newline="") as f:
        out = [{k: _value(v, columns[k]) for k, v in r.items() if k in columns} for r in csv.DictReader(f)]
    for r in out:
        if str(r.get("boundary") or "").startswith("custom:"):
            r["boundary"] = None
    return out


def seed(engine):
    """Gives a database without any region the reference data. {table: rows added} (empty when it had some)."""
    with engine.begin() as conn:
        if conn.execute(select(func.count()).select_from(Region.__table__)).scalar():
            return {}
        added = {}
        for filename, model in TABLES:
            data = rows(filename, model)
            if data:
                conn.execute(insert(model.__table__), data)
            added[model.__tablename__] = len(data)
        if conn.dialect.name == "postgresql":  # ids came from the files: the next ones follow them
            for _, model in TABLES:
                t = model.__tablename__
                conn.execute(text(f"SELECT setval(pg_get_serial_sequence('{t}', 'id'), "
                                  f"COALESCE((SELECT MAX(id) FROM {t}), 0) + 1, false)"))
    if any(added.values()):
        log.info("Reference data added: %s", ", ".join(f"{n} {t}" for t, n in added.items()))
    return added


def norm(text):
    """A name as a key: case, accents and punctuation aside, in any script (Malvasia Σητείας)."""
    t = "".join(c for c in unicodedata.normalize("NFKD", str(text or "")).casefold() if not unicodedata.combining(c))
    return " ".join(re.findall(r"\w+", t))


def _names(row):
    """A row's name and its aliases (comma separated)."""
    return [row["name"]] + [a for a in (row.get("aliases") or "").split(",") if a.strip()]


def keys(table, row, regions):
    """A row's stable keys ({column: value}; regions: {region id: (name, country)}), its name's first, then its
    aliases' (a row is found by any of them; the first is the one recorded)."""
    region, country = regions.get(row.get("region_id")) or (None, None)
    if table in ("regions", "varietals", "producers"):
        return [norm(n) for n in _names(row)]
    if table == "appellations":
        return [f"{norm(n)}|{norm(country)}" for n in _names(row)]
    boundary = row.get("boundary") or ""  # vineyards
    return ([boundary] if boundary and not boundary.startswith("custom:") else []) + [f"{norm(row['name'])}|{norm(region)}"]


def update(engine, commit=True):
    """Brings the shipped reference data into the database (see above). {"baseline": True} the first time (keys
    recorded, nothing changed), else {table: {"added", "filled", "skipped"}}; nothing saved without commit."""
    conn = engine.connect()
    trans = conn.begin()
    try:
        keys_table = ReferenceKey.__table__
        received = {(t, k) for t, k in conn.execute(select(keys_table.c.table_name, keys_table.c.key))}
        baseline = not received
        csv_regions = {r["id"]: (r["name"], r["country"]) for r in rows("regions.csv", Region)}
        region_ids = {}  # the CSV's region id -> this database's
        report, new_keys = {}, []
        for filename, model in TABLES:
            table, t = model.__tablename__, model.__table__
            db_regions = {r.id: (r.name, r.country) for r in conn.execute(select(Region.__table__))}
            found = {}
            for r in conn.execute(select(t)).mappings():
                for k in keys(table, r, db_regions):
                    found.setdefault(k, r)
            added = filled = skipped = 0
            for r in rows(filename, model):
                row_keys = keys(table, r, csv_regions)
                key = row_keys[0]
                existing = next((found[k] for k in row_keys if k in found), None)
                if (table, key) not in received:
                    new_keys.append({"table_name": table, "key": key})
                if baseline:
                    continue
                values = {c: v for c, v in r.items() if c != "id" and v is not None}
                if "region_id" in values:
                    values["region_id"] = region_ids.get(values["region_id"])
                if existing is None:
                    if (table, key) in received:
                        continue  # deleted or renamed here: stays so
                    if "region_id" in r and r["region_id"] is not None and values.get("region_id") is None:
                        skipped += 1  # its region isn't here (deleted): left out
                        continue
                    conn.execute(insert(t), values)
                    added += 1
                    continue
                empty = {c: v for c, v in values.items() if existing.get(c) in (None, "")}
                if empty:
                    conn.execute(sql_update(t).where(t.c.id == existing["id"]).values(**empty))
                    filled += 1
            if table == "regions":
                by_name = {norm(name): rid for rid, name in conn.execute(select(Region.id, Region.name))}
                region_ids = {cid: by_name.get(norm(name)) for cid, (name, _) in csv_regions.items()}
            report[table] = {"added": added, "filled": filled, "skipped": skipped}
        seen = set()
        new_keys = [k for k in new_keys if (k["table_name"], k["key"]) not in seen and not seen.add((k["table_name"], k["key"]))]
        if new_keys:
            conn.execute(insert(keys_table), new_keys)
        (trans.commit if commit else trans.rollback)()
    except Exception:
        trans.rollback()
        raise
    finally:
        conn.close()
    if baseline:
        return {"baseline": True}
    changes = ", ".join(f"{t}: {n['added']} added, {n['filled']} filled" for t, n in report.items() if n["added"] or n["filled"])
    if changes and commit:
        log.info("Reference data updated: %s", changes)
    return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from db import engine
    import migrate
    dry = "--dry-run" in sys.argv
    if not dry:
        migrate.upgrade(engine)
        print(seed(engine) or "The database has regions already: nothing seeded.")
    print(update(engine, commit=not dry))
    sys.exit(0)
