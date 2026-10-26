"""Data integrity: tasting notes whose bottle is gone, bottles whose wine is gone. Also on the app's Settings page."""
import os
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import config  # noqa: E402

DB_URL = config.DB_URL


def find_orphans(session):
    """{"notes": [(note id, bottle id, notes)], "bottles": [(bottle id, wine id, location)], "totals": {...}}"""
    notes = session.execute(text("""
        SELECT t.id, t.bottle_id, t.notes FROM tasting_notes t
        LEFT JOIN cellar b ON t.bottle_id = b.id WHERE b.id IS NULL ORDER BY t.id""")).fetchall()
    bottles = session.execute(text("""
        SELECT b.id, b.wine_id, b.location FROM cellar b
        LEFT JOIN wines w ON b.wine_id = w.id WHERE w.id IS NULL ORDER BY b.id""")).fetchall()
    totals = {t: session.execute(text(f"SELECT count(*) FROM {t}")).scalar()
              for t in ("wines", "cellar", "tasting_notes")}
    return {"notes": [tuple(r) for r in notes], "bottles": [tuple(r) for r in bottles], "totals": totals}


def check_orphans():
    session = sessionmaker(bind=create_engine(DB_URL))()
    try:
        r = find_orphans(session)
        print("--- DATA INTEGRITY CHECK ---")
        print(f"Notes with missing bottles: {len(r['notes'])}")
        for note_id, bottle_id, notes in r["notes"]:
            print(f"  - Note ID {note_id} (Bottle {bottle_id}): {(notes or '')[:50]}...")
        print(f"Bottles with missing wines: {len(r['bottles'])}")
        for bottle_id, wine_id, location in r["bottles"]:
            print(f"  - Bottle ID {bottle_id} (Wine {wine_id}) at {location}")
        print(f"\nTotal Wines: {r['totals']['wines']}")
        print(f"Total Bottles: {r['totals']['cellar']}")
        print(f"Total Notes: {r['totals']['tasting_notes']}")
    finally:
        session.close()


if __name__ == "__main__":
    check_orphans()
