"""Duplicate wines: same producer, cuvée, color, appellation, grape, vintage and disgorgement. Their cellar lines (and
so their tasting notes, which point at the lines) move to the oldest wine of the group, which takes over what it
lacks (critics' scores, LWIN, drinking window...); each emptied duplicate is then deleted. The orphan check runs
before committing and undoes everything if it finds one.

    python app/api/tasks/consolidate_duplicate_wines.py            # dry run
    python app/api/tasks/consolidate_duplicate_wines.py --commit

The same functions back the Settings page's maintenance section in the app.
"""
import argparse
import os
import sys
from collections import defaultdict

from sqlalchemy import create_engine
from sqlalchemy.orm import joinedload, sessionmaker

# app/api on the path (models, paths, tasks), for running this file as a script
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tasks.housekeeping.check_orphans import find_orphans  # noqa: E402
from tasks.merge_cuvees import carry  # noqa: E402
from models import Bottle, Wine  # noqa: E402


def find_duplicate_groups(session):
    """[{"label", "primary": wine id, "duplicates": [wine ids], "bottles": {wine id: [bottles]}}], biggest first."""
    groups = defaultdict(list)
    wines = session.query(Wine).options(joinedload(Wine.producer), joinedload(Wine.appellation),
                                        joinedload(Wine.varietal)).all()
    for w in wines:
        # Color too: a red and a white of one cuvée name are two wines
        groups[(w.producer_id, w.cuvee or "", w.type, w.appellation_id, w.varietal_id, w.vintage,
                w.disgorgement_date)].append(w)
    out = []
    for ws in groups.values():
        if len(ws) < 2:
            continue
        ws.sort(key=lambda w: w.id)
        first = ws[0]
        vintage = (first.vintage or "NV") + (f" - {first.disgorgement_date}" if first.disgorgement_date else "")
        label = " · ".join(x for x in (
            first.producer.name if first.producer else "N/A", first.cuvee,
            first.appellation.name if first.appellation else None,
            first.varietal.name if first.varietal else None, vintage) if x)
        dups = [w.id for w in ws[1:]]
        bottles = {i: session.query(Bottle).filter(Bottle.wine_id == i).all() for i in dups}
        out.append({"label": label, "primary": first.id, "duplicates": dups, "bottles": bottles})
    return sorted(out, key=lambda g: (-len(g["duplicates"]), g["label"].lower()))


def merge_groups(session, groups, log=print):
    """Moves the duplicates' cellar lines to each group's primary wine, carries over what the primary lacks,
    deletes the emptied duplicates. Commits; undoes everything (ValueError) if anything would be orphaned.
    Cellar lines moved."""
    before = find_orphans(session)
    moved = 0
    for g in groups:
        primary = session.get(Wine, g["primary"])
        for dup_id, bottles in g["bottles"].items():
            for b in bottles:
                b.wine_id = g["primary"]
                moved += 1
            dup = session.get(Wine, dup_id)
            carry(primary, dup)
            session.flush()
            if session.query(Bottle).filter(Bottle.wine_id == dup_id).count():
                session.rollback()
                raise ValueError(f"wine {dup_id} still has cellar lines after the move: nothing changed")
            session.delete(dup)
            session.flush()
        log(f"{g['label']}: wines {', '.join(map(str, g['duplicates']))} -> {g['primary']} "
            f"({sum(len(b) for b in g['bottles'].values())} cellar lines moved), duplicates deleted")
    after = find_orphans(session)
    if len(after["notes"]) > len(before["notes"]) or len(after["bottles"]) > len(before["bottles"]):
        session.rollback()
        raise ValueError("The merge would leave orphan cellar lines or tasting notes: nothing changed")
    session.commit()
    return moved


def describe(groups, log=print):
    for g in groups:
        log(f"{g['label']}")
        log(f"  keep wine {g['primary']}, merge {g['duplicates']}")
        for dup_id, bottles in g["bottles"].items():
            for b in bottles:
                log(f"    - bottle {b.id} (wine {dup_id}): {b.qty}x {b.bottle_size or '75cl'} @ {b.location or 'no location'}")


def consolidate_duplicate_wines(dry_run=True, limit=None):
    import paths
    session = sessionmaker(bind=create_engine(paths.DB_URL))()
    try:
        groups = find_duplicate_groups(session)[:limit] if limit else find_duplicate_groups(session)
        if not groups:
            print("No duplicate wines found.")
            return
        print(f"\n{'DRY RUN - ' if dry_run else ''}{len(groups)} groups of duplicate wines\n")
        describe(groups)
        bottles = sum(len(b) for g in groups for b in g["bottles"].values())
        if dry_run:
            print(f"\n⚠ DRY RUN: {bottles} cellar lines would move and {sum(len(g['duplicates']) for g in groups)} "
                  f"duplicate wines be deleted. Run with --commit to apply.")
        else:
            print(f"\n✓ {merge_groups(session, groups, log=lambda _: None)} bottles moved")
    finally:
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Consolidate duplicate wines by merging bottles.")
    parser.add_argument("--commit", action="store_true", help="Actually commit changes (default is dry-run)")
    args = parser.parse_args()
    consolidate_duplicate_wines(dry_run=not args.commit, limit=30)
