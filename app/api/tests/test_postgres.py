"""The schema on Postgres, as the NAS runs it (the other tests use SQLite): migrations up, the models' schema, the
reference data (its Postgres-only step), all migrations down and up again. Skipped without TEST_PG_URL (CI's
postgres job sets it: an empty database it may drop everything in)."""
import os

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy import MetaData, create_engine, inspect, text

import migrate

PG = os.getenv("TEST_PG_URL")
pytestmark = pytest.mark.skipif(not PG, reason="TEST_PG_URL not set: no Postgres to test against")


def seed(session):
    """No rows: these tests make their own database"""


def test_postgres_schema_reference_and_round_trip():
    from test_schema import head, model_tables, revision
    import reference
    engine = create_engine(PG)
    with engine.begin() as c:  # a clean slate
        c.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
    migrate.upgrade(engine)
    assert revision(engine) == head()
    target = MetaData()
    for table in model_tables().values():
        table.to_metadata(target)
    with engine.connect() as c:
        diff = compare_metadata(MigrationContext.configure(c, opts={"compare_type": True}), target)
    assert diff == [], diff
    added = reference.seed(engine)
    assert added and all(n >= 0 for n in added.values())
    # every migration undone, then done again: each one's downgrade works on Postgres
    with engine.begin() as c:
        c.execute(text("TRUNCATE TABLE " + ", ".join(t for t in inspect(c).get_table_names() if t != "alembic_version") + " CASCADE"))
        command.downgrade(migrate.config(c), "base")
    assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
    migrate.upgrade(engine)
    assert revision(engine) == head()
    engine.dispose()
