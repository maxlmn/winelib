"""Duplicate producers: one domaine entered under two names ("Place Of Changing Winds" / "Place of Changing Winds",
"Bodegas Vega Sicilia" / "Vega Sicilia"), found and merged.

Two producers look like one when their names are the same without accents, case and punctuation, or have the same
distinctive words (no "Domaine", "Bodegas", "Weingut", initials: app/api/tasks/matching.py). It's a guess
("Château L'Enclos" and "Domaine de l'Enclos" aren't one): the report lists them, you pick.

Merging moves the dropped producer's wines to the kept one; a wine the kept producer already has (same cuvée,
color, appellation, grape, vintage and disgorgement) gives it its cellar lines and is deleted, as when merging
cuvées. The kept producer takes the details it lacks (region, website...); notes and descriptions are joined. Then
the dropped producer is deleted. Nothing but wines points at a producer.

    python app/api/tasks/merge_producers.py                         # the likely duplicates
    python app/api/tasks/merge_producers.py --keep 12 --drop 40     # dry run
    python app/api/tasks/merge_producers.py --keep 12 --drop 40 --commit

The same functions back Settings › Maintenance › Duplicate producers.
"""
import argparse
import os
import sys
from collections import Counter, defaultdict

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tasks.housekeeping.check_orphans import find_orphans  # noqa: E402
from tasks.matching import distinctive, norm  # noqa: E402
from tasks.merge_cuvees import _empty, fold, twin_of  # noqa: E402
from models import Producer, Wine  # noqa: E402

FILLED = ("region_id", "subregion", "village", "winemaker", "owner", "type", "importers", "profile_url", "lists",
          "website")
JOINED = ("notes", "description")


def find_similar_producers(session):
    """[{"a": (id, name, wines), "b": (id, name, wines), "reason"}], producers with the most wines first."""
    counts = Counter(dict(session.query(Wine.producer_id, func.count(Wine.id)).group_by(Wine.producer_id).all()))
    producers = session.query(Producer).order_by(Producer.id).all()
    groups = defaultdict(list)  # (reason, key) -> producers
    for p in producers:
        groups[("Same name", norm(p.name))].append(p)
        groups[("Same distinctive words", " ".join(sorted(distinctive(p.name))))].append(p)
    pairs, seen = [], set()
    for (reason, key), ps in groups.items():
        if not key:
            continue
        for i, a in enumerate(ps):
            for b in ps[i + 1:]:
                if (a.id, b.id) in seen:
                    continue
                seen.add((a.id, b.id))
                why = reason if reason == "Same name" else f"{reason}: {key}"
                pairs.append({"a": (a.id, a.name, counts[a.id]), "b": (b.id, b.name, counts[b.id]), "reason": why})
    pairs.sort(key=lambda p: (-(p["a"][2] + p["b"][2]), p["a"][1].lower()))
    return pairs


def merge_producer(session, keep_id, drop_id, log=print):
    """Merges producer `drop_id` into `keep_id`, without committing: the caller commits or rolls back.
    {"moved": n, "merged": n, "lines_moved": n, "filled": [fields]}. Raises ValueError (and changes nothing the
    caller keeps) when a producer is missing or the merge would orphan a cellar line or a tasting note."""
    if keep_id == drop_id:
        raise ValueError("Pick two different producers")
    keep, drop = session.get(Producer, keep_id), session.get(Producer, drop_id)
    if keep is None or drop is None:
        raise ValueError(f"No producer {keep_id if keep is None else drop_id}")
    before = find_orphans(session)
    moved = merged = lines = 0
    for w in session.query(Wine).filter(Wine.producer_id == drop.id).order_by(Wine.id).all():
        twin = twin_of(session, w, keep.id, w.cuvee)
        if twin is None:
            w.producer_id = keep.id
            moved += 1
            continue
        n = fold(session, w, twin)
        merged += 1
        lines += n
        log(f"wine {w.id} ({w.cuvee or '-'} {w.vintage or 'NV'}): already at {keep.name}, {n} cellar lines → "
            f"wine {twin.id}, then deleted")
    filled = []
    for field in FILLED:
        if _empty(getattr(keep, field)) and not _empty(getattr(drop, field)):
            setattr(keep, field, getattr(drop, field))
            filled.append(field)
    for field in JOINED:
        mine, theirs = (getattr(keep, field) or "").strip(), (getattr(drop, field) or "").strip()
        if theirs and theirs not in mine:
            setattr(keep, field, f"{mine}\n\n{theirs}" if mine else theirs)
            filled.append(field)
    session.flush()
    # its list entries follow it (its own, and its wines': moved or merged above, their producer is now keep)
    from models import ListItem
    session.query(ListItem).filter(ListItem.producer_id == drop.id).update({ListItem.producer_id: keep.id})
    session.expire(drop, ["wines"])
    session.delete(drop)
    session.flush()
    log(f"“{drop.name}” → “{keep.name}”: {moved} wines moved, {merged} merged into the same wine"
        + (f", took {', '.join(filled)}" if filled else ""))
    after = find_orphans(session)
    if len(after["notes"]) > len(before["notes"]) or len(after["bottles"]) > len(before["bottles"]):
        raise ValueError("The merge would leave orphan cellar lines or tasting notes: nothing changed")
    return {"moved": moved, "merged": merged, "lines_moved": lines, "filled": filled}


def main():
    parser = argparse.ArgumentParser(description="Find or merge duplicate producers.")
    parser.add_argument("--keep", type=int, help="Producer id to keep")
    parser.add_argument("--drop", type=int, help="Producer id to merge into it")
    parser.add_argument("--commit", action="store_true", help="Apply (default: dry run)")
    args = parser.parse_args()
    import paths
    session = sessionmaker(bind=create_engine(paths.DB_URL))()
    try:
        if args.keep is None or args.drop is None:
            for p in find_similar_producers(session):
                print(f"{p['a'][0]:>5} {p['a'][1]} ({p['a'][2]})  /  {p['b'][0]} {p['b'][1]} ({p['b'][2]})  "
                      f"[{p['reason']}]")
            return
        r = merge_producer(session, args.keep, args.drop)
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
