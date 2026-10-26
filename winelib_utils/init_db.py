#!/usr/bin/env python3
"""A new database: the schema (the app's migrations, app/api/migrate.py) and the reference data (regions,
appellations, grapes, vineyards from app/api/data/reference/, app/api/reference.py). The app does the same at each start,
so this is only needed to prepare a database before running it.

    python winelib_utils/init_db.py        # DB_URL, else data/winelib.db
"""
import logging
import os
import sys

API_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "api")
sys.path.insert(0, API_DIR)

import migrate  # noqa: E402
import reference  # noqa: E402
from db import engine  # noqa: E402

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    migrate.upgrade(engine)
    added = reference.seed(engine)
    print(f"Ready: {engine.url.render_as_string(hide_password=True)}"
          + (f" ({', '.join(f'{n} {t}' for t, n in added.items())} added)" if added else " (it had reference data already)"))
