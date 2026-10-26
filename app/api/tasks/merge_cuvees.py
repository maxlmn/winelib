"""Merges two spellings of one producer's cuvée ("Poyeux" into "Les Poyeux"), e.g. from the similar cuvée names
report (app/api/tasks/housekeeping/find_similar_cuvees.py).

Each wine of the dropped cuvée either:
- has a twin under the kept name (same color, appellation, grape, vintage and disgorgement): its cellar lines move to
  the twin (their tasting notes follow, they point at the lines), the twin takes over what it lacks (critics'
  scores, LWIN, drinking window, vineyard, blend), then the emptied wine is deleted; or
- has none: it's renamed.
Nothing points at a wine but cellar lines, so nothing is left dangling; the orphan check runs before committing
and undoes everything if it finds one.

    python app/api/tasks/merge_cuvees.py --producer 12 --drop "Poyeux" --keep "Les Poyeux"            # dry run
    python app/api/tasks/merge_cuvees.py --producer 12 --drop "Poyeux" --keep "Les Poyeux" --commit

The same function backs the Similar cuvée names report on the app's Settings page.
"""
import argparse
import os
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tasks.housekeeping.check_orphans import find_orphans  # noqa: E402
from models import Bottle, Wine  # noqa: E402

# Taken from the dropped wine when its twin has none (and each critic's score: carry())
CARRIED = ("lwin", "drink_window_start", "drink_window_end", "vineyard_id", "blend")


def _empty(value):
    return value in (None, "", "-", "0")


def carry(twin, w):
    """Gives the twin what w has and it lacks: the CARRIED fields, and each critic's score (with its note, link and
    date) the twin has none from."""
    for field in CARRIED:
        if _empty(getattr(twin, field)) and not _empty(getattr(w, field)):
            setattr(twin, field, getattr(w, field))
    for s in w.scores:
        mine = twin.score_of(s.critic)
        if mine is None or (_empty(mine.score) and not _empty(s.score)):
            twin.set_score(s.critic, s.score, s.note, s.url, s.date)


def twin_of(session, w, producer_id, cuvee):
    """The wine `w` would be under that producer and cuvée: same color, appellation, grape, vintage and
    disgorgement."""
    return (session.query(Wine)
            .filter(Wine.producer_id == producer_id, Wine.cuvee == cuvee, Wine.id != w.id,
                    Wine.appellation_id == w.appellation_id, Wine.varietal_id == w.varietal_id,
                    Wine.vintage == w.vintage, Wine.disgorgement_date == w.disgorgement_date,
                    Wine.type == w.type)
            .order_by(Wine.id).first())


def fold(session, w, twin):
    """Moves w's cellar lines to its twin, gives the twin what it lacks, deletes w. The number of lines moved."""
    lines = session.query(Bottle).filter(Bottle.wine_id == w.id).all()
    for b in lines:
        b.wine_id = twin.id
    carry(twin, w)
    session.flush()
    left = session.query(Bottle).filter(Bottle.wine_id == w.id).count()
    if left:
        raise ValueError(f"wine {w.id} still has {left} cellar lines after the move")
    session.delete(w)
    session.flush()
    return len(lines)


def merge_cuvee(session, producer_id, drop, keep, log=print):
    """Merges cuvée `drop` into `keep` for one producer, without committing: the caller commits or rolls back.
    {"renamed": n, "merged": n, "lines_moved": n}. Raises ValueError (and changes nothing) when the merge
    would orphan a cellar line or a tasting note."""
    if drop == keep:
        raise ValueError("Pick two different cuvée names")
    before = find_orphans(session)
    wines = session.query(Wine).filter(Wine.producer_id == producer_id, Wine.cuvee == drop).order_by(Wine.id).all()
    renamed = merged = moved = 0
    for w in wines:
        twin = twin_of(session, w, producer_id, keep)
        if twin is None:
            w.cuvee = keep
            renamed += 1
            log(f"wine {w.id} ({w.vintage or 'NV'}): renamed “{drop}” → “{keep}”")
            continue
        n = fold(session, w, twin)
        merged += 1
        moved += n
        log(f"wine {w.id} ({w.vintage or 'NV'}): {n} cellar lines → wine {twin.id}, then deleted")
    after = find_orphans(session)
    if len(after["notes"]) > len(before["notes"]) or len(after["bottles"]) > len(before["bottles"]):
        raise ValueError("The merge would leave orphan cellar lines or tasting notes: nothing changed")
    return {"renamed": renamed, "merged": merged, "lines_moved": moved}


def main():
    parser = argparse.ArgumentParser(description="Merge two spellings of a producer's cuvée.")
    parser.add_argument("--producer", type=int, required=True, help="Producer id")
    parser.add_argument("--drop", required=True, help="Cuvée name to merge away")
    parser.add_argument("--keep", required=True, help="Cuvée name to keep")
    parser.add_argument("--commit", action="store_true", help="Apply (default: dry run)")
    args = parser.parse_args()
    import paths
    session = sessionmaker(bind=create_engine(paths.DB_URL))()
    try:
        r = merge_cuvee(session, args.producer, args.drop, args.keep)
        if args.commit:
            session.commit()
            print(f"✓ Done: {r}")
        else:
            session.rollback()
            print(f"DRY RUN: {r}. Run with --commit to apply.")
    except ValueError as e:
        session.rollback()
        print(f"❌ {e}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
