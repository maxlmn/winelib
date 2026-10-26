# The app: FastAPI + SvelteKit

```
app/
├── api/   FastAPI on the SQLAlchemy models (winelib_utils/models.py); migrations in api/migrations/
└── web/   SvelteKit (Svelte 5, a static single-page app) with MapLibre GL
```

`python run.py` at the repository's root serves both on one port: the API under `/api/`, the built web app for
everything else. For development, run them apart.

## Develop

The API, from `app/api` (Python 3.11+):

```bash
pip install -r requirements.txt -r requirements-dev.txt
uvicorn main:app --reload --port 8000
```

It uses `data/winelib.db` (SQLite) unless `DB_URL` says otherwise (Postgres works too). A new database is
migrated and seeded with the reference data (`api/data/reference/`) at startup.

The web app, from `app/web` (Node 22):

```bash
npm install
API_URL=http://localhost:8000 npx vite dev
```

## Check

- `pytest` in `app/api`: each test module gets its own SQLite database.
- `npm run check` in `app/web`: Svelte and TypeScript.
- `python scripts/check_imports.py`: the app imports with `app/api/requirements.txt` alone.

## Change the schema

Edit `winelib_utils/models.py`, then from `app/api`:

```bash
python migrate.py revision "what changed"
```

Read the migration it writes (data to move, a default for existing rows): it runs at the next start, on every
installation. `tests/test_schema.py` fails if the models and the migrations disagree.

## Where things are

- **Reference data**: `api/data/reference/*.csv` (regions, appellations, grapes, producers, vineyards), with stable
  keys so updates reach existing installations (`api/reference.py`). How they were built: `api/data/docs/`.
- **Map outlines**: the shape store in `data/geo/shapes/`, built by `geo_scripts/` (see its README) or installed
  from the map pack (Settings › Maintenance).
- **Your data**: the database, `data/images/` (tasting photos), `backups/`. `api/paths.py` decides where: `data/` in
  a checkout, your user folder for a release.
- **Plug-ins**: Python modules in `plugins/` (not part of this repository), each with a `register(api)` that can add
  a router, a Maintenance task or a wine-page action (`api/plugins.py`). The app works fully without any.
