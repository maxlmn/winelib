from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

import paths  # where the files are

# The tables: models.py
from models import (  # noqa: F401
    Appellation, Base, Bottle, CriticScore, CustomShape, Place, Producer, ReferenceKey, Region, RestaurantVisit,
    TastingNote, Varietal, Vineyard, Wine, WineGrape, WineList, ListItem, BottleEvent, WineTag, TastingTag,
)

DB_URL = paths.DB_URL
connect_args = {"check_same_thread": False} if DB_URL.startswith("sqlite") else {}
engine = create_engine(DB_URL, connect_args=connect_args, pool_pre_ping=True)
Session = sessionmaker(bind=engine)


def sqlite_pragmas(engine):
    """SQLite as a server's database: WAL (pages read while a Maintenance job writes), a few seconds' wait for
    another writer instead of "database is locked", and lower() for every letter as Postgres's (SQLite's own lowers
    A-Z only: a grape named "Muscat Blanc À Petits Grains" wasn't found by its name)."""
    if engine.dialect.name != "sqlite":
        return

    @event.listens_for(engine, "connect")
    def _pragmas(conn, _):
        cur = conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA busy_timeout=5000")
        cur.close()
        conn.create_function("lower", 1, lambda s: s.lower() if isinstance(s, str) else s, deterministic=True)


sqlite_pragmas(engine)


def get_session():
    import settings
    session = Session()
    try:
        settings.refresh(session)  # pick up edits made from another process or after a restart
        yield session
    finally:
        session.close()


def same(col, value):
    """col == value, NULL matching NULL (plain == never matches a NULL cuvée, appellation or grape)."""
    return col.is_(None) if value is None else col == value


def same_cuvee(cuvee):
    """Filter for wines of this cuvée name. No name is stored both as NULL (wines added from the app's form
    before October 2026) and as '' (everything older): both count as one."""
    from sqlalchemy import func
    return func.coalesce(Wine.cuvee, "") == (cuvee or "")
