"""Prepares INAO's parcel delimitation of the wine AOCs (data.gouv.fr, "Délimitation parcellaire des AOC viticoles",
Licence Ouverte 2.0) for the shape store: its wine parcels merged

- per appellation -> data/geo/france.parquet (source inao, linked by the appellations' INAO id);
- per premier cru (a denomination other than its appellation, with "premier cru" in its name: Burgundy's, and
  Chaume in the Loire) -> data/geo/vineyards/vineyards_premier_crus_inao.parquet (source vineyard, ids inao-pc:<id>).

    python geo_scripts/etl_inao_fr.py appellations
    python geo_scripts/etl_inao_fr.py vineyards      # then build_shapes.py --only inao,vineyard and the shape links

Unzip the shapefile download into data/geo/ first (a folder named like 2026-02-02-delim-parcellaire-aoc-shp: the
newest one is read). Its parcels are millions of small polygons: expect several GB of memory and some minutes.
"""
import glob
import os
import sys

import geopandas as gpd
import pandas as pd

GEO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "geo")
SIMPLIFY = 0.0001  # degrees, ~10 m; build_shapes.py simplifies further for display


def parcels():
    """The wine parcels of the newest download, in lon/lat, their geometries made valid."""
    found = sorted(glob.glob(os.path.join(GEO, "*delim-parcellaire*", "*.shp")))
    if not found:
        sys.exit("No INAO parcel shapefile in data/geo (a *delim-parcellaire*/ folder): download it first (geo_scripts/README.md)")
    print(f"Reading {os.path.relpath(found[-1], GEO)}...")
    gdf = gpd.read_file(found[-1], engine="pyogrio")
    gdf = gdf[gdf["type_prod"] == "Vins"].to_crs("EPSG:4326")
    gdf["geometry"] = gdf.geometry.buffer(0)  # fixes self-intersections
    return gdf


def save(gdf, path, what):
    gdf["geometry"] = gdf.simplify(tolerance=SIMPLIFY, preserve_topology=True)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    gdf.to_parquet(path)
    print(f"{len(gdf)} {what} -> {os.path.relpath(path, GEO)}")


def appellations():
    save(parcels().dissolve(by="app", as_index=False), os.path.join(GEO, "france.parquet"), "appellations")


def premier_crus():
    gdf = parcels()
    gdf = gdf[(gdf["app"] != gdf["denom"]) & gdf["denom"].str.contains("premier cru", case=False, na=False)]
    gdf = gdf.rename(columns={"id_denom": "id"})
    gdf["id"] = pd.to_numeric(gdf["id"], errors="coerce").fillna(0).astype(int)
    save(gdf.dissolve(by="denom", as_index=False, aggfunc="first"),
         os.path.join(GEO, "vineyards", "vineyards_premier_crus_inao.parquet"), "premier crus")


if __name__ == "__main__":
    tasks = {"appellations": appellations, "vineyards": premier_crus}
    if len(sys.argv) != 2 or sys.argv[1] not in tasks:
        sys.exit(f"usage: python geo_scripts/etl_inao_fr.py {' | '.join(tasks)}")
    tasks[sys.argv[1]]()
