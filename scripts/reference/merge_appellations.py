"""Merges duplicate appellations: rows that are one denomination under two names, found through the shape they
share (the `boundary` column, app/api/shape_links.py).

- EU: every row linked to one PDO is that PDO under another name (an alias, an old name, a typo, Greek or Cyrillic
  script). The row named as in the EU register is kept: in Latin script when there is one, the register's main name
  first, then the one with most wines.
- INAO: rows sharing an outline are often different appellations (a village and its premier crus, Alsace and Alsace
  Grand Cru), so only a bare grand cru of type "Wine" ("Chambertin") merges into its "<name> Grand Cru".
- SKIP: groups that are distinct wines of one PDO, or a row linked by mistake: never merged.

Merging moves the dropped rows' wines to the kept one, fills the kept row's empty columns from them, then deletes
them. Only wines point at an appellation.

    python scripts/reference/merge_appellations.py              # preview: every group, what's kept, what moves
    python scripts/reference/merge_appellations.py --commit
"""
import argparse
import os
import re
import sys
import unicodedata

from sqlalchemy import create_engine, text

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

# Distinct wines sharing a PDO: kept apart
SKIP = {"Cinque Terre Sciacchetrà", "Moscato di Pantelleria", "Passito di Pantelleria",
        # a designation within the PDO, its own wines: Classico, Superiore, Aszú
        "Tokaji Aszú", "Valpolicella Classico", "Valpolicella Superiore", "Soave Classico", "Bolgheri Superiore"}
# Duplicates without a shape to find them by: kept name <- dropped names
BY_NAME = {"Cádiz": ["Cadiz"]}
# Filled on the kept row from a dropped one when empty
FILLED = ("region_id", "subregion", "type", "details", "colors", "location_link", "winemap_name", "pdo_id", "category",
          "varieties_text", "max_yield_hl", "max_yield_kg", "municipalities", "registration_date", "inao_id")


def comparable(name):
    text_ = "".join(c for c in unicodedata.normalize("NFKD", str(name or "")) if not unicodedata.combining(c))
    return re.sub(r"[\W_]+", " ", text_.casefold()).strip()


def _store_names(geo_dir):
    """{source_id: [comparable names]} of the EU shapes (each of "A / B")."""
    import pyarrow.parquet as pq
    path = os.path.join(geo_dir, "shapes", "eu.parquet")
    if not os.path.exists(path):
        return {}
    t = pq.read_table(path, columns=["source_id", "name"]).to_pydict()
    return {sid: [comparable(n) for n in str(name or "").split(" / ")] for sid, name in zip(t["source_id"], t["name"])}


def plan(conn, geo_dir):
    """[(boundary, keep row, [dropped rows])]; rows are dicts with id, name, type, wines."""
    rows = [dict(r._mapping) for r in conn.execute(text(
        "SELECT a.id, a.name, a.type, a.pdo_id, a.boundary, (SELECT count(*) FROM wines w WHERE w.appellation_id = a.id) "
        "AS wines FROM appellations a WHERE a.boundary IN (SELECT boundary FROM appellations WHERE boundary IS NOT NULL "
        "GROUP BY boundary HAVING count(*) > 1) ORDER BY a.boundary, a.id"))]
    groups = {}
    for r in rows:
        groups.setdefault(r["boundary"], []).append(r)
    official = _store_names(geo_dir)
    out = []
    for boundary, members in groups.items():
        members = [r for r in members if r["name"] not in SKIP]
        if len(members) < 2:
            continue
        if boundary.startswith("eu:"):
            names = official.get(boundary.split(":", 1)[1], [])

            def rank(r):
                c = comparable(r["name"])
                # Latin script first (Santorini over Σαντορίνη), then the register's names in its order, then wines
                return (bool(re.search(r"[^\x00-\x7f]", c) and not re.search(r"[a-z]", c)),
                        names.index(c) if c in names else len(names), -r["wines"], not r["pdo_id"], r["id"])
            keep = sorted(members, key=rank)[0]
            out.append((boundary, keep, [r for r in members if r is not keep]))
        elif boundary.startswith("inao:"):
            for bare in [r for r in members if (r["type"] or "") == "Wine"]:
                cru = [r for r in members if r is not bare and comparable(r["name"]) == comparable(bare["name"]) + " grand cru"]
                if not cru:  # hyphens and spaces differ: "Clos-De-La-Roche Grand Cru" / "Clos de la Roche"
                    cru = [r for r in members if r is not bare and comparable(r["name"]).replace(" ", "")
                           == (comparable(bare["name"]) + " grand cru").replace(" ", "")]
                if len(cru) == 1:
                    out.append((boundary, cru[0], [bare]))
    named = {r.name: dict(r._mapping) for r in conn.execute(text(
        "SELECT a.id, a.name, a.type, a.pdo_id, a.boundary, (SELECT count(*) FROM wines w WHERE w.appellation_id = a.id) "
        "AS wines FROM appellations a WHERE a.name = ANY(:n)"), {"n": [*BY_NAME, *sum(BY_NAME.values(), [])]})}
    for keep, drops in BY_NAME.items():
        if keep in named and any(d in named for d in drops):
            out.append(("name", named[keep], [named[d] for d in drops if d in named]))
    return out


def merge(conn, keep_id, drop_ids):
    """Moves the wines, fills the kept row's empty columns, deletes the dropped rows. Wines moved."""
    moved = 0
    for drop_id in drop_ids:
        for col in FILLED:
            conn.execute(text(f"UPDATE appellations k SET {col} = d.{col} FROM appellations d WHERE k.id = :k AND d.id = :d "
                              f"AND (k.{col} IS NULL OR k.{col}::text = '') AND d.{col} IS NOT NULL AND d.{col}::text <> ''"),
                         {"k": keep_id, "d": drop_id})
        moved += conn.execute(text("UPDATE wines SET appellation_id = :k WHERE appellation_id = :d"),
                              {"k": keep_id, "d": drop_id}).rowcount
        conn.execute(text("DELETE FROM appellations WHERE id = :d"), {"d": drop_id})
    return moved


def main(db_url, geo_dir, commit=False):
    engine = create_engine(db_url)
    with engine.begin() as conn:
        groups = plan(conn, geo_dir)
        dropped = moved = 0
        for boundary, keep, drops in groups:
            print(f"{boundary}: keep “{keep['name']}” ({keep['wines']} wines) <- "
                  + ", ".join(f"“{d['name']}” ({d['wines']} wines)" for d in drops))
            if commit:
                moved += merge(conn, keep["id"], [d["id"] for d in drops])
            dropped += len(drops)
        left = conn.execute(text("SELECT count(*) FROM wines w WHERE w.appellation_id IS NOT NULL AND NOT EXISTS "
                                 "(SELECT 1 FROM appellations a WHERE a.id = w.appellation_id)")).scalar()
        if left:
            raise SystemExit(f"{left} wines would point at a deleted appellation: nothing saved")
        verb = "Merged" if commit else "Would merge"
        print(f"\n{verb} {dropped} appellations into {len(groups)} ({moved if commit else sum(d['wines'] for _, _, ds in groups for d in ds)} wines moved).")
        if not commit:
            print("Preview: nothing saved. Run with --commit to save.")


if __name__ == "__main__":
    import config
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--commit", action="store_true")
    parser.add_argument("--geo-dir", default=os.getenv("GEO_DIR") or os.path.join(PROJECT_ROOT, "data", "geo"))
    args = parser.parse_args()
    main(os.getenv("DB_URL") or config.DB_URL, args.geo_dir, args.commit)
