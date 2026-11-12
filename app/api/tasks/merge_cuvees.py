"""Merges two spellings of one producer's cuvée ("Poyeux" into "Les Poyeux"), e.g. from the similar cuvée names
report (app/api/tasks/housekeeping/find_similar_cuvees.py).

Each wine of the dropped cuvée either:
- has a twin under the kept name (same color, appellation, grape, vintage and disgorgement): its cellar lines move to
  the twin (their tasting notes follow, they point at the lines), the twin takes over what it lacks (critics'
  scores, grapes and shares, region, LWIN, drinking window, vineyard, blend...), then the emptied wine is deleted; or
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

# Never taken from the dropped wine: what makes it that wine (and the main grape, which follows its grapes)
KEPT = ("id", "producer_id", "cuvee", "vintage", "varietal_id")


def _empty(value):
    return value in (None, "", "-", "0")


def _grapes(twin, w):
    """The twin's grapes after taking w's: the more complete list of the two (more known shares, then more grapes;
    the twin's on a tie) in its order, then the grapes only the other has. A share missing on one side is taken
    from the other, and the other's shares are added only while they keep the total at 100% or under. None when
    the twin's list is already complete."""
    def rows(x):
        return [(g.varietal, g.share) for g in x.grapes if g.varietal is not None]
    mine, theirs = rows(twin), rows(w)
    if not theirs:
        return None

    def rank(gs):
        return (sum(1 for _, s in gs if s is not None), len(gs))
    base, other = (theirs, mine) if rank(theirs) > rank(mine) else (mine, theirs)
    share_of = {v.id: s for v, s in other}
    total = sum(s for _, s in base if s is not None)
    out = []
    for v, s in base:
        if s is None and share_of.get(v.id) is not None and total + share_of[v.id] <= 100:
            s = share_of[v.id]
            total += s
        out.append((v, s))
    have = {v.id for v, _ in out}
    for v, s in other:
        if v.id in have:
            continue
        if s is not None and total + s > 100:
            s = None
        total += s or 0
        out.append((v, s))
    return None if out == mine else out


def _join(a, b):
    a, b = (a or "").strip(), (b or "").strip()
    return a if not b or b in a else f"{a}\n\n{b}" if a else b


def carry(twin, w):
    """Gives the twin what w has and it lacks: every field it has empty (region, vineyard, LWIN, drinking window,
    blend...), w's grapes and shares it lacks, each critic's score (with its note, link and date) the twin has none
    from, its list entries (one per list: an entry of both keeps the twin's, with w's note), its style tags and its
    uploaded label (when the twin has none)."""
    for col in Wine.__table__.columns:
        if col.key in KEPT:
            continue
        if _empty(getattr(twin, col.key)) and not _empty(getattr(w, col.key)):
            setattr(twin, col.key, getattr(w, col.key))
    grapes = _grapes(twin, w)
    if grapes is not None:
        twin.set_grapes(grapes)
    for s in w.scores:
        mine = twin.score_of(s.critic)
        if mine is None or (_empty(mine.score) and not _empty(s.score)):
            twin.set_score(s.critic, s.score, s.note, s.url, s.date)
    from sqlalchemy.orm import object_session
    from models import ListItem, WineTag
    session = object_session(w)
    if session is not None:  # and its list entries, and the style tags set on it
        theirs = {(i.list_id, i.kind): i for i in session.query(ListItem).filter(ListItem.wine_id == twin.id)}
        for item in session.query(ListItem).filter(ListItem.wine_id == w.id).all():
            kept = theirs.get((item.list_id, item.kind))
            if kept is not None:  # the list has the twin already: one entry, the notes of both
                kept.note = _join(kept.note, item.note) or None
                session.delete(item)
            else:
                item.wine_id, item.producer_id = twin.id, twin.producer_id
                theirs[(item.list_id, item.kind)] = item
        if w.id is not None and twin.id is not None:
            import photos
            photos.move_label(w.id, twin.id)
        has = {t for t, in session.query(WineTag.tag).filter(WineTag.wine_id == twin.id)}
        for row in session.query(WineTag).filter(WineTag.wine_id == w.id).all():
            if row.tag in has:
                session.delete(row)
            else:
                row.wine_id = twin.id


def twin_of(session, w, producer_id, cuvee):
    """The wine `w` would be under that producer and cuvée: same color, appellation, grape, vintage and
    disgorgement (no name or disgorgement, NULL or '', counts as one)."""
    from sqlalchemy import func
    return (session.query(Wine)
            .filter(Wine.producer_id == producer_id, func.coalesce(Wine.cuvee, "") == (cuvee or ""), Wine.id != w.id,
                    Wine.appellation_id == w.appellation_id, Wine.varietal_id == w.varietal_id,
                    Wine.vintage == w.vintage,
                    func.coalesce(Wine.disgorgement_date, "") == (w.disgorgement_date or ""),
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
