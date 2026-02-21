#!/usr/bin/env python3
"""
Initialize the WineLib database.

Creates all tables and optionally seeds reference data (regions, appellations,
varietals, vineyards) from bundled CSV files.

Usage:
    python init_db.py          # Create tables + seed reference data
    python init_db.py --skip-seed   # Create tables only

This script only runs when using SQLite. For PostgreSQL, manage your 
database schema separately.
"""
import os
import sys
import csv
import argparse
from datetime import date as date_type, datetime

# Ensure this directory is in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from models import Base, Region, Appellation, Varietal, Vineyard
from sqlalchemy import create_engine, Integer, Float, Date
from sqlalchemy.orm import sessionmaker

# --- Config ---
DATA_DIR = os.path.join(CURRENT_DIR, "data")
SEED_DIR = os.path.join(DATA_DIR, "seed")
DB_URL = os.getenv("DB_URL", f"sqlite:///{os.path.join(DATA_DIR, 'winelib.db')}")


def init_db(seed=True):
    """Create tables and optionally seed reference data."""
    
    # Safety check: only auto-run on SQLite
    if not DB_URL.startswith("sqlite"):
        print(f"[WARN] DB_URL points to a non-SQLite database: {DB_URL}")
        print("       init_db is designed for fresh SQLite setups only.")
        print("       If you really want to initialize this database, set FORCE_INIT=1")
        if not os.getenv("FORCE_INIT"):
            sys.exit(1)
    
    os.makedirs(DATA_DIR, exist_ok=True)
    
    connect_args = {"check_same_thread": False} if DB_URL.startswith("sqlite") else {}
    engine = create_engine(DB_URL, connect_args=connect_args)
    
    # Create all tables
    print(f"[*] Creating tables in: {DB_URL}")
    Base.metadata.create_all(engine)
    print("[OK] Tables created successfully.")
    
    if not seed:
        print("[SKIP] Skipping seed data (--skip-seed)")
        return
    
    if not os.path.exists(SEED_DIR):
        print(f"[WARN] Seed directory not found: {SEED_DIR}")
        print("       Run without seed data or add CSV files to data/seed/")
        return
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        _seed_table(session, "regions.csv", Region)
        _seed_table(session, "appellations.csv", Appellation)
        _seed_table(session, "varietals.csv", Varietal)
        _seed_table(session, "vineyards.csv", Vineyard)
        session.commit()
        print("\n[DONE] Database initialized successfully!")
    except Exception as e:
        session.rollback()
        print(f"\n[ERROR] Error seeding data: {e}")
        raise
    finally:
        session.close()


def _coerce_value(value, column):
    """Convert a CSV string value to the appropriate Python type for a column."""
    if value == "" or value is None:
        return None
    
    col_type = type(column.type)
    
    if col_type is Integer or issubclass(col_type, Integer):
        # Handle float-like strings (e.g. "80.0") by converting via float first
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None
    
    if col_type is Float or issubclass(col_type, Float):
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    if col_type is Date or issubclass(col_type, Date):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None
    
    return value


def _seed_table(session, csv_filename, model_class):
    """Load a CSV file into a database table, skipping existing records."""
    csv_path = os.path.join(SEED_DIR, csv_filename)
    
    if not os.path.exists(csv_path):
        print(f"  [SKIP] {csv_filename} not found, skipping.")
        return
    
    table_name = model_class.__tablename__
    existing_count = session.query(model_class).count()
    
    if existing_count > 0:
        print(f"  [SKIP] {table_name}: already has {existing_count} records, skipping.")
        return
    
    # Read CSV and insert
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    if not rows:
        print(f"  [SKIP] {csv_filename} is empty, skipping.")
        return
    
    # Build column lookup: name -> Column object
    columns = {c.name: c for c in model_class.__table__.columns}
    
    count = 0
    for row in rows:
        filtered = {}
        for k, v in row.items():
            if k in columns:
                filtered[k] = _coerce_value(v, columns[k])
        
        obj = model_class(**filtered)
        session.add(obj)
        count += 1
    
    session.flush()
    print(f"  [OK] {table_name}: loaded {count} records from {csv_filename}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize WineLib database")
    parser.add_argument("--skip-seed", action="store_true", help="Skip seeding reference data")
    args = parser.parse_args()
    
    init_db(seed=not args.skip_seed)
