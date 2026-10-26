"""Alembic's environment: the app's database (db.engine, or the connection migrate.py passes) and every table's
model, for `alembic revision --autogenerate` (run from app/api: see migrate.py)."""
import os
import sys

from alembic import context
from sqlalchemy import MetaData

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # app/api

import settings  # noqa: E402  (app_settings has its own metadata)
from db import Base, engine  # noqa: E402

target_metadata = MetaData()
for md in (Base.metadata, settings.Base.metadata):
    for table in md.tables.values():
        table.to_metadata(target_metadata)


def run():
    connection = context.config.attributes.get("connection")
    if connection is None:
        with engine.connect() as connection:
            return _migrate(connection)
    _migrate(connection)


def _migrate(connection):
    # render_as_batch: SQLite can't ALTER most things; batch mode copies the table instead
    context.configure(connection=connection, target_metadata=target_metadata,
                      render_as_batch=connection.dialect.name == "sqlite", compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


run()
