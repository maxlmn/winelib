# WineLib 🍷

A personal wine cellar management app built with [Streamlit](https://streamlit.io/).

Track your wines, tasting notes, producers, appellations, and vineyards — with interactive maps showing appellation boundaries and vineyard polygons across 20+ countries.

## Quick Start

```bash
git clone https://github.com/maxlmn/winelib.git
cd winelib
pip install -r requirements.txt
python init_db.py
streamlit run app.py
```

The app opens at `http://localhost:8501`.

## Features

### 📊 Dashboard
- Year-over-year tasting stats with Altair charts
- Breakdown by wine color, region, and vintage
- Cellar value summary with multi-currency support (EUR, USD, SGD, etc.)

### 🏠 Cellar Inventory
- Track bottles by location, purchase date, price, and format
- Multi-currency pricing with automatic conversion
- Filter by color, region, producer, and storage location
- Visual card view grouped by location, with bottle icons colored by wine type
- Direct links to bottle, wine, and producer detail pages

### 📝 Tasting Notes
- Log ratings (100-point scale), tasting notes, food pairings, and tags
- Track glasses consumed 
- Organize as a tasting journal — group notes by date and place with photo support
- Card view showing restaurant visits with wine lineups
- Timeline and list views with full filtering

### 👨‍🌾 Producer Directory
- Browse producers by region, subregion, village, and winemaker
- Curated list tags (e.g. "The New French Wine", "World Atlas of Wine")
- Full-text search across producer names
- Detail pages showing wine catalog, cellar inventory, and tasting history per producer

### 🍽️ Places & Restaurant Visits
- Track restaurants, bars, and tasting venues
- Michelin star display (⭐⭐⭐)
- Visit count tracking across tastings and dedicated visits
- Detail pages with interactive maps (Google Places integration)

### 🗺️ Interactive Wine Maps
- Cascading Region → Appellation → Vineyard filters
- Appellation boundary polygons for 20+ countries (EU PDO data + French INAO + US AVAs)
- Vineyard-level polygons (Burgundy Premier Crus, German Weinlagen, and more)
- Multiple tile layers (OpenStreetMap, Satellite, Terrain)
- Click-to-navigate from map polygons to detail pages

### 🏷️ Appellation Explorer
- 1,600+ appellations with PDO metadata (registration dates, permitted yields, grape varieties)
- Linked wines, producers, and vineyard listings per appellation
- Map view with boundary polygons on detail pages

### 🍇 Reference Data
- 110+ grape varietals with aliases
- 7,300+ vineyards with region/village/sub-region hierarchy
- 55 wine regions across France, Italy, Spain, Germany, USA, Argentina, and more

### ✏️ Full CRUD
- Add/edit/delete forms for: wines, bottles, tasting notes, producers, places, and restaurant visits
- Smart wine selector with type-ahead search by producer, appellation, and vintage
- Inline creation of new wines, producers, and appellations from any form

## Database

By default, WineLib uses **SQLite** — no server needed. The database is created at `data/winelib.db` on first run with pre-loaded reference data (regions, appellations, varietals, vineyards).

To use **PostgreSQL** instead, set the `DB_URL` environment variable:

```bash
export DB_URL="postgresql://user:pass@localhost:5432/winelib"
pip install psycopg2-binary
```

## Geo Data (Optional)

Map polygon overlays require parquet files in `data/geo/`. These are not included in the repo due to their size (~140 MB).

The app works fine without them — maps display markers but no polygon boundaries.

## Project Structure

```
├── app.py              # Main app and routing
├── models.py           # SQLAlchemy models (10 tables)
├── shared.py           # Database config, session management, utilities
├── geo_utils.py        # Folium map helpers, parquet loaders
├── forms.py            # All CRUD forms
├── ui_utils.py         # Table rendering, color coding, navigation
├── constants.py        # UI constants, currencies, bottle sizes
├── init_db.py          # Database initialization + seed data loader
├── requirements.txt
├── data/
│   ├── seed/           # Reference CSVs (regions, appellations, varietals, vineyards)
│   ├── geo/            # Parquet map data (gitignored, optional)
│   └── winelib.db      # SQLite database (gitignored, auto-created)
├── views/
│   ├── summary.py      # Dashboard with charts
│   ├── cellar.py       # Cellar inventory
│   ├── tasting_history.py  # Tasting journal
│   ├── directory.py    # Producers & Places lists
│   ├── map.py          # Interactive wine map
│   ├── details.py      # All detail pages (producer, wine, bottle, appellation, vineyard, place)
│   └── components.py   # Shared card components
└── .streamlit/config.toml  # Theme (dark mode)
```

## Tech Stack

- **[Streamlit](https://streamlit.io/)** — UI framework
- **[SQLAlchemy](https://www.sqlalchemy.org/)** — ORM (SQLite / PostgreSQL)
- **[Folium](https://python-visualization.github.io/folium/)** — Interactive maps
- **[GeoPandas](https://geopandas.org/)** — Geospatial data (parquet polygons)
- **[Altair](https://altair-viz.github.io/)** — Charts and visualizations

## License

MIT
