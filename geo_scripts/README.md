# geo_scripts: building the map's outlines

The map draws appellations and vineyards from the **shape store**: `data/geo/shapes/`, one GeoParquet file per
source plus `manifest.json`. These scripts build it from the public sources, on your computer:

1. download each source's files into `data/geo/`;
2. prepare them (one script per source);
3. build the store with `build_shapes.py`;
4. link your appellations and vineyards to their outlines (shape links).

Or skip all of it: Settings › Maintenance › *Map outlines* downloads the ready-made map pack, built by
`build_map_pack.py` from a store like this one.

The scripts need the geo libraries (`geopandas`, `shapely`, `pyarrow`: in `app/api/requirements.txt`). Run them from the repository root; everything goes under `data/geo/` (git-ignored).

## 1–2. Sources

Every source is optional: the store holds those you prepared.

| Source | Download (into `data/geo/`) | Licence | Prepare | Gives (`build_shapes.py` source) |
|---|---|---|---|---|
| **INAO parcels** | data.gouv.fr, *Délimitation parcellaire des AOC viticoles*: the shapefile, unzipped (a `…delim-parcellaire-aoc-shp/` folder) | Licence Ouverte 2.0 | `python geo_scripts/etl_inao_fr.py appellations`<br>`python geo_scripts/etl_inao_fr.py vineyards` | each AOC's vines (`inao`); the premier crus (`vineyard`, `inao-pc:<id>`) |
| **INAO denominations and areas** | the parcels above, plus data.gouv.fr *Délimitation des aires géographiques des SIQO*: the `delim-aire-geographique` shapefile, unzipped into `inao_aires/` | Licence Ouverte 2.0 | `python geo_scripts/build_inao_areas.py` | each AOC and complementary name's vines (`inao_denom`); appellation and IGP areas (`inao_aires`) |
| **EU PDOs** | figshare collection 5877659 (Candiago et al. 2022, doi.org/10.6084/m9.figshare.c.5877659): `EU_PDO.gpkg` and `PDO_EU_id.json` | CC0 1.0 | `python geo_scripts/etl_gpkg_pdo.py` | every EU wine PDO (`eu`) |
| **US AVAs** | downloaded by the script (UC Davis Library, github.com/UCDavisLibrary/ava) | CC0 1.0 | `python geo_scripts/download_ava_data.py` | every AVA (`ava`) |
| **Australian GIs** | Wine Australia Open Data Hub, *Wine Geographical Indications Australia* (the current item, not the "superseded" one): each layer as GeoJSON into `australia/` | CC BY 4.0 | nothing: read as downloaded | zones, regions, subregions (`au`) |
| **Administrative areas** | downloaded by the script (Natural Earth admin-1, ~15 MB) | public domain | `python geo_scripts/build_admin_areas.py` | appellations that are a prefecture, canton, IGT region... (`admin`; the list is in the script) |

INAO's parcel file is large: millions of small polygons, several GB of memory and some minutes to merge.

Your own outlines: put the files under `data/geo/` (GeoJSON, Shapefile, GeoPackage, GeoParquet, KML; any
coordinate system), describe them in `data/geo/sources.local.json` (same format as `app/api/data/shape_sources.json`,
whose `_doc` explains the fields: a source named like a shipped one replaces it, others are added), and build with
`--only <name>`. One row at a time is simpler from the app: *Draw outline* on an appellation or vineyard page.

## 3. The store

```bash
python geo_scripts/build_shapes.py                   # every source whose files are there
python geo_scripts/build_shapes.py --only inao,au    # some of them
```

Each file has the same columns: `source`, `source_id` (what a link names: `inao:291`), `name`, `level`,
`geometry` (the outline as prepared), `display` (simplified for the map) and its box. The map draws `display`; an
appellation or vineyard page's *Full detail* shows `geometry`. Rerun after downloading a source again.

`python geo_scripts/geo_inventory.py` lists what's in `data/geo` and what reads each file (changes nothing).

## 4. Shape links

Each appellation and vineyard row names its outline in its `boundary` column (`inao:291`, `eu:PDO-IT-A0281`,
`vineyard:inao-pc:257`), by its INAO or PDO id, or by name (each source's `link` rules in `shape_sources.json`).
Run Settings › Maintenance › *Shape links* (a preview, then save), or on a computer with the database:

```bash
python geo_scripts/link_shapes.py            # dry run: what would be linked, and what can't be
python geo_scripts/link_shapes.py --commit
```

Rerun after rebuilding the store or adding appellations. Names that differ from a source's go in its `aliases`
(`shape_sources.json`), or in `ALIASES` (`app/api/shape_links.py`) for Australia.

## Other scripts

- `build_region_outlines.py`: the map's overview, one coarse outline per wine region from Natural Earth
  (`app/api/data/region_outlines.geojson`, committed). Rerun after adding a region to its list.
- `build_map_pack.py`: the map pack, from your store: the sources whose licence allows it, with their credits,
  display outlines only (`dist/winelib-map-pack.zip`).
- Your own sources (files that can't ship, a vineyard source you built): list them in `data/geo/sources.local.json`,
  merged over the shipped `app/api/data/shape_sources.json` (its `_doc` says how).
