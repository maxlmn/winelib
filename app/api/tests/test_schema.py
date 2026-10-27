"""The migrations make the models' schema, for a new database and for one stamped at the last pre-release revision.
Run from app/api:  pytest"""
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import MetaData, create_engine, inspect, text

import migrate
from db import Base


def model_tables():
    import settings
    return {t.name: t for md in (Base.metadata, settings.Base.metadata) for t in md.tables.values()}


def revision(engine):
    with engine.connect() as c:
        return c.execute(text("SELECT version_num FROM alembic_version")).scalar()


def head():
    return ScriptDirectory.from_config(migrate.config()).get_current_head()


def test_a_new_database_gets_the_schema_of_the_models(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'new.db'}")
    migrate.upgrade(engine)
    migrate.upgrade(engine)  # twice: nothing more to do
    assert revision(engine) == head()
    for name, table in model_tables().items():
        assert {c["name"] for c in inspect(engine).get_columns(name)} == set(table.c.keys()), name


def test_migrations_match_the_models(tmp_path):
    """A model change without its migration fails here."""
    engine = create_engine(f"sqlite:///{tmp_path / 'new.db'}")
    migrate.upgrade(engine)
    target = MetaData()
    for table in model_tables().values():
        table.to_metadata(target)
    with engine.connect() as c:
        diff = compare_metadata(MigrationContext.configure(c, opts={"compare_type": True}), target)
    assert diff == [], diff


def test_a_database_at_the_last_revision_before_the_release(tmp_path):
    """0011, the last migration before they were squashed into one 0001 at the release: its schema is 0001's, the
    database is re-stamped 0001 (0011 no longer exists) and upgraded from there to the head."""
    from alembic import command
    engine = create_engine(f"sqlite:///{tmp_path / 'before.db'}")
    with engine.begin() as c:
        command.upgrade(migrate.config(c), "0001")
    with engine.begin() as c:
        c.execute(text("UPDATE alembic_version SET version_num = '0011'"))
    migrate.upgrade(engine)
    assert revision(engine) == head()
