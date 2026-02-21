import sys
import os
import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure this directory is in sys.path for local imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from models import Producer, Wine, Bottle, TastingNote, Appellation, Varietal, Place, RestaurantVisit, Vineyard, Region

__all__ = [
    "Producer", "Wine", "Bottle", "TastingNote", "Appellation", 
    "Varietal", "Place", "RestaurantVisit", "Vineyard", "Region",
    "get_all_regions", "get_region_colors_map", "get_or_create_region",
    "get_region_name", "get_session", "TYPE_COLORS", "ISO_MAP", "EXCHANGE_RATES",
    "DB_URL", "engine", "Session", "AVAILABLE_TILESETS"
]

# --- DATABASE ---
# PostgreSQL via DB_URL env var (e.g. docker-compose), or SQLite by default
DATA_DIR = os.path.join(CURRENT_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

DB_URL = os.getenv("DB_URL", f"sqlite:///{os.path.join(DATA_DIR, 'winelib.db')}")
connect_args = {"check_same_thread": False} if DB_URL.startswith("sqlite") else {}
engine = create_engine(DB_URL, connect_args=connect_args)
Session = sessionmaker(bind=engine)

def get_session():
    return Session()

# --- CACHED METADATA ---
@st.cache_data
def get_all_regions():
    """Fetch all regions from the database."""
    session = get_session()
    try:
        return session.query(Region).all()
    finally:
        session.close()

@st.cache_data
def get_region_colors_map():
    """Returns a dictionary of region names to hex colors from the DB."""
    regs = get_all_regions()
    return {r.name: r.color for r in regs if r.color}

def get_or_create_region(session, name):
    """Get a region by name or create a new one if it doesn't exist."""
    if not name or str(name).strip() == "": return None
    name = name.strip()
    reg = session.query(Region).filter_by(name=name).first()
    if not reg:
        reg = Region(name=name)
        session.add(reg)
        session.flush()
    return reg

def get_region_name(obj):
    """Safely get region name from a model object (Appellation, Wine, etc.)"""
    try:
        if hasattr(obj, 'region_obj') and obj.region_obj:
            return obj.region_obj.name
    except: pass
    return None

# --- CONSTANTS ---
EXCHANGE_RATES = {
    "SGD": 1.0, "EUR": 1.45, "USD": 1.35, "GBP": 1.70, "AUD": 0.90
}

# Obsidian-inspired color palette for both themes
# (These are now in the database, REGION_COLORS removed)

TYPE_COLORS = {
    "Red": ("#660000", "white"),
    "White": ("#ffe599", "black"),
    "Bubbles": ("#fff2cc", "black"),
    "Rose": ("#d5a6bd", "black"),
    "Sweet": ("#e69138", "white"),
    "Fortified": ("#e6e6e6", "#9487dfff"),
    "Orange": ("#e69138", "black"),
}

ISO_MAP = {
    "IT": "italy", "FR": "france", "ES": "spain", "DE": "germany",
    "PT": "portugal", "AT": "austria", "BE": "belgium", "BG": "bulgaria",
    "CY": "cyprus", "CZ": "czech_republic", "EL": "greece", "GR": "gr",
    "HU": "hungary", "HR": "croatia", "LU": "luxembourg", "MT": "malta",
    "NL": "netherlands", "PL": "poland", "RO": "romania", "SI": "slovenia",
    "SK": "slovakia", "GB": "united_kingdom", "DK": "dk"
}

# Additional tilesets to include in layer control (user can switch between them)
AVAILABLE_TILESETS = [
    #"OpenStreetMap",
    "OpenStreetMap.France", 
    "OpenTopoMap",
    #"CartoDB positron",
    #"CartoDB dark_matter",
    #"Stadia.AlidadeSatellite"
]