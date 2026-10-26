"""Prepares INAO's French outlines for the shape store, from two data.gouv.fr files (Licence Ouverte):

- the parcel delimitation (data/geo/*delim-parcellaire*/*.shp, the file etl_inao_fr.py reads): its wine parcels merged
  per denomination (id_denom), so each AOC and each complementary geographic name ("Coteaux du Layon Faye-d'Anjou",
  "Mâcon Pierreclos", "Bourgogne Hautes Côtes de Nuits") gets the outline of the vines it covers
  -> data/geo/inao_denoms/denominations.parquet (source inao_denom);
- the geographic areas (data/geo/inao_aires/*delim-aire-geographique*.shp): the area where a wine may be made.
  Only appellations and IGPs are kept: a complementary name's area is usually its whole appellation's (Faye-d'Anjou's
  is all of Coteaux du Layon), which would draw the parent under the village's name
  -> data/geo/inao_aires/areas.parquet (source inao_aires: the IGPs, which have no parcels).

    python geo_scripts/build_inao_areas.py        # then build_shapes.py --only inao_denom,inao_aires and the links

Both are written in lon/lat (the denominations simplified to ~5 m); build_shapes.py simplifies for display.
"""
import glob
import os
import sys

import geopandas as gpd
import numpy as np
import shapely

GEO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "geo")
SIMPLIFY = 0.00005  # degrees, ~5 m: finer than any map zoom shows, and the store's display outline is coarser still


def one(pattern):
    found = sorted(glob.glob(os.path.join(GEO, pattern)))
    if not found:
        sys.exit(f"Nothing in data/geo for {pattern}")
    return found[-1]  # the newest dated download


def denominations():
    src = one("*delim-parcellaire*/*.shp")
    print(f"Reading {os.path.relpath(src, GEO)}...")
    gdf = gpd.read_file(src, columns=["type_prod", "type_denom", "id_app", "app", "id_denom", "denom", "signe"])
    gdf = gdf[(gdf.type_prod == "Vins") & gdf.id_denom.notna()].to_crs("EPSG:4326")
    rows = []
    for (id_denom, denom), part in gdf.groupby(["id_denom", "denom"], sort=False):
        geom = shapely.union_all(shapely.make_valid(np.array(part.geometry.values, dtype=object)))
        geom = shapely.simplify(geom, SIMPLIFY, preserve_topology=True)  # parcels to ~5 m: a tenth of the size
        rows.append({"id_denom": int(id_denom), "denom": denom, "app": part.app.iloc[0], "type_denom": part.type_denom.iloc[0],
                     "geometry": geom})
    out = gpd.GeoDataFrame(rows, crs="EPSG:4326")
    path = os.path.join(GEO, "inao_denoms", "denominations.parquet")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    out.to_parquet(path)
    print(f"{len(out)} denominations ({(out.type_denom != 'appellation').sum()} complementary names) -> {os.path.relpath(path, GEO)}")


def areas():
    src = one("inao_aires/*delim-aire-geographique*.shp")
    print(f"Reading {os.path.relpath(src, GEO)}...")
    gdf = gpd.read_file(src, columns=["type_denom", "id_app", "app", "id_denom", "denom", "signe", "categorie"])
    gdf = gdf[(gdf.type_denom == "appellation") & gdf.id_denom.notna()].to_crs("EPSG:4326")
    gdf["id_denom"] = gdf.id_denom.astype(int)
    path = os.path.join(GEO, "inao_aires", "areas.parquet")
    gdf.to_parquet(path)
    print(f"{len(gdf)} appellation and IGP areas ({(gdf.signe == 'IGP').sum()} IGP) -> {os.path.relpath(path, GEO)}")


if __name__ == "__main__":
    denominations()
    areas()
