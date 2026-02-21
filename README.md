# WineLib

A personal wine cellar management application built with [Streamlit](https://streamlit.io/).

Track your wines, tasting notes, producers, appellations, and vineyards — with interactive maps showing appellation boundaries and vineyard polygons.

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/maxlmn/winelib.git
cd winelib
pip install -r requirements.txt

# 2. Initialize the database (SQLite)
python init_db.py

# 3. Run
streamlit run app.py
```

The app opens at `http://localhost:8501`.

## Features

- **Cellar Inventory** — Track bottles by location, purchase date, and price
- **Tasting Notes** — Log ratings, notes, and food pairings
- **Producer Database** — Organize by region, village, and classification
- **Appellation Explorer** — Browse 1,600+ appellations with PDO metadata
- **Interactive Maps** — View appellation boundaries and vineyard polygons (requires geo data)
- **Varietal & Vineyard Reference** — 110+ varietals, 7,300+ vineyards

## Database

By default, WineLib uses **SQLite** — no server needed. The database is created at `data/winelib.db` on first run.

To use **PostgreSQL** instead, set the `DB_URL` environment variable:

```bash
export DB_URL="postgresql://user:pass@localhost:5432/winelib"
```

Or create a `.env` file (see `.env.example`).

## Geo Data (Optional)

Map polygon overlays require parquet files in `data/geo/`. These are not included in the repo due to their size (~140 MB).

The app works without them — maps will display markers but no polygon boundaries.

## Project Structure

```
├── app.py              # Main Streamlit app
├── models.py           # SQLAlchemy models
├── shared.py           # Database config and shared utilities
├── geo_utils.py        # Map utilities (Folium/GeoPandas)
├── init_db.py          # Database initialization + seed data
├── requirements.txt    # Python dependencies
├── data/
│   ├── seed/           # Reference data CSVs (regions, appellations, etc.)
│   ├── geo/            # Parquet map data (gitignored)
│   └── winelib.db      # SQLite database (gitignored)
├── views/              # Page views (cellar, tastings, map, etc.)
└── .streamlit/         # Streamlit theme config
```

## License

MIT
