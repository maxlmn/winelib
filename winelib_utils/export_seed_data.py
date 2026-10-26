#!/usr/bin/env python3
"""
Export reference data from the current PostgreSQL database to seed CSVs.
Outputs to app/api/data/reference/, which the app (app/api/reference.py) seeds new databases from. Regions, appellations and
grapes whole; vineyards only INAO's public premier crus (PUBLIC_VINEYARDS); producers without what's yours
(PRIVATE_PRODUCER_COLUMNS: notes, lists, importers, and the descriptions and profile links, copied text).
"""
import os
import sys
import csv

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

import config
from winelib_utils.models import Base, Region, Appellation, Varietal, Vineyard, Producer
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

SEED_DIR = os.path.join(PROJECT_ROOT, "app", "api", "data", "reference")  # shipped with the app

# The only vineyards that ship: the premier crus of INAO's public parcel data (Etalab licence), outlined by its shapes
# (vineyard:inao-pc:<id>). The others (Weinlagen, lieux-dits, your own) stay in your database.
PUBLIC_VINEYARDS = "vineyard:inao-pc:"
# A producer ships with its name, aliases, region, sub-region, village, type, owner and winemaker (its website: no,
# often a retailer's page)
PRIVATE_PRODUCER_COLUMNS = ["notes", "lists", "importers", "description", "profile_url", "website"]


def export_table(session, model_class, filename, exclude_cols=None, where=None):
    """Export a table (the rows `where` keeps) to CSV."""
    exclude = set(exclude_cols or [])
    
    columns = [c.name for c in model_class.__table__.columns if c.name not in exclude]
    query = session.query(model_class)
    rows = (query.filter(where) if where is not None else query).order_by(model_class.id).all()
    
    filepath = os.path.join(SEED_DIR, filename)
    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            out = {col: getattr(row, col) for col in columns}
            if str(out.get("boundary") or "").startswith("custom:"):  # an outline drawn in the app: yours
                out["boundary"] = None
            writer.writerow(out)
    
    print(f"✅ Exported {len(rows)} rows to {filename}")

def main():
    os.makedirs(SEED_DIR, exist_ok=True)
    
    engine = create_engine(config.DB_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Export reference tables (exclude geojson from vineyards — it's large and in parquets)
        export_table(session, Region, "regions.csv")
        export_table(session, Appellation, "appellations.csv", exclude_cols=["geojson"])
        export_table(session, Varietal, "varietals.csv")
        export_table(session, Vineyard, "vineyards.csv", exclude_cols=["geojson"],
                     where=Vineyard.boundary.like(PUBLIC_VINEYARDS + "%"))
        export_table(session, Producer, "producers.csv", exclude_cols=PRIVATE_PRODUCER_COLUMNS)
        
        print(f"\n🎉 Seed data exported to {SEED_DIR}")
    finally:
        session.close()

if __name__ == "__main__":
    main()
