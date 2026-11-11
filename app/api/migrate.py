"""Database migrations (Alembic, migrations/): run at startup so every database, yours and anyone's, has the
schema the code expects. A database made before migrations (it has tables but no alembic_version) is taken as the
baseline (0001) first, then upgraded like any other.

A schema change: edit app/api/models.py, then from app/api
    python migrate.py revision "add critic_scores"     # writes migrations/versions/<rev>_....py (autogenerate)
read and adjust it (data to move, a default for existing rows), and it runs at the next start. By hand:
    python migrate.py upgrade                           # DB_URL, else data/winelib.db
    python migrate.py current
"""
import logging
import os
import sys

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

HERE = os.path.dirname(os.path.abspath(__file__))
BASELINE = "0001"
# The public release squashed the migrations before it (0001 to 0011) into one 0001: a database at the last of them
# already has that schema, and is re-stamped at it
SQUASHED = {"0011": BASELINE}
log = logging.getLogger(__name__)


def config(connection=None):
    cfg = Config()
    cfg.set_main_option("script_location", os.path.join(HERE, "migrations"))
    cfg.attributes["connection"] = connection
    return cfg


def copy_before(engine):
    """The SQLite database copied to backups/ before a migration changes it (before-<revision>.sqlite, one per
    revision left): SQLite doesn't undo a half-run schema change, so a migration that fails could leave a database
    the app can't open. The copy's path, or None when there's nothing to migrate (or it isn't SQLite: pg_dump is
    yours)."""
    import sqlite3
    import paths
    file = engine.url.database
    if engine.dialect.name != "sqlite" or not file or not os.path.isfile(file):
        return None
    with engine.connect() as conn:
        if "alembic_version" not in set(inspect(conn).get_table_names()):
            return None  # a new database, or one from before migrations (its first stamp changes nothing)
        current = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        head = ScriptDirectory.from_config(config(conn)).get_current_head()
    if not current or current == head or SQUASHED.get(current) == head:
        return None
    os.makedirs(paths.BACKUP_DIR, exist_ok=True)
    target = os.path.join(paths.BACKUP_DIR, f"before-{current}.sqlite")
    source, copy = sqlite3.connect(file), sqlite3.connect(target)
    try:
        source.backup(copy)
    finally:
        source.close()
        copy.close()
    log.info("The database copied to %s before its migration (%s to %s)", target, current, head)
    return target


def upgrade(engine):
    """Brings the database to the latest revision (stamping an older, unversioned one as the baseline first)."""
    copied = copy_before(engine)
    try:
        _upgrade(engine)
    except Exception:
        if copied:
            log.error("The migration failed. The database as it was is in %s: put it back in place of %s "
                      "(with the version of WineLib you had) to go on as before.", copied, engine.url.database)
        raise


def _upgrade(engine):
    with engine.begin() as conn:
        cfg = config(conn)
        names = set(inspect(conn).get_table_names())
        if "alembic_version" not in names and "wines" in names:
            log.info("A database from before migrations: taken as revision %s", BASELINE)
            command.stamp(cfg, BASELINE)
        elif "alembic_version" in names:
            current = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
            known = {s.revision for s in ScriptDirectory.from_config(cfg).walk_revisions()}
            if current in SQUASHED and current not in known:
                log.info("Revision %s was squashed at the release: re-stamped as %s", current, SQUASHED[current])
                command.stamp(cfg, SQUASHED[current], purge=True)
        command.upgrade(cfg, "head")


def main(argv):
    from db import engine
    if not argv or argv[0] == "upgrade":
        upgrade(engine)
    elif argv[0] == "current":
        with engine.connect() as conn:
            command.current(config(conn), verbose=True)
    elif argv[0] == "revision" and len(argv) > 1:
        with engine.begin() as conn:
            command.revision(config(conn), message=argv[1], autogenerate=True)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main(sys.argv[1:])
