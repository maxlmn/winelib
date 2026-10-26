"""Prepares the EU wine PDOs for the shape store, from Candiago et al. (2022), "A geospatial inventory of regulatory
information for wine protected designations of origin in Europe" (figshare, CC0: doi.org/10.6084/m9.figshare.c.5877659):
its outlines (EU_PDO.gpkg) joined with its PDO ids and names (PDO_EU_id.json), one file per country
-> data/geo/<country>_pdo.parquet (source eu).

    python geo_scripts/etl_gpkg_pdo.py               # then build_shapes.py --only eu and the shape links

Put EU_PDO.gpkg and PDO_EU_id.json from the collection in data/geo/ first.
"""
import json
import os
import sys

import geopandas as gpd
import pandas as pd

GEO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "geo")
# ISO code -> the file's name (data/geo/<name>_pdo.parquet)
COUNTRIES = {
    "IT": "italy", "FR": "france", "ES": "spain", "DE": "germany", "PT": "portugal", "AT": "austria",
    "BE": "belgium", "BG": "bulgaria", "CY": "cyprus", "CZ": "czech_republic", "EL": "greece", "HU": "hungary",
    "HR": "croatia", "LU": "luxembourg", "MT": "malta", "NL": "netherlands", "PL": "poland", "RO": "romania",
    "SI": "slovenia", "SK": "slovakia", "GB": "united_kingdom",
}
COLUMNS = ["pdo_id", "name", "category", "country", "registration", "geometry"]


def main():
    gpkg, ids = os.path.join(GEO, "EU_PDO.gpkg"), os.path.join(GEO, "PDO_EU_id.json")
    for path in (gpkg, ids):
        if not os.path.exists(path):
            sys.exit(f"Missing {os.path.normpath(path)}: download it from the figshare collection (geo_scripts/README.md)")
    print("Reading the outlines and the PDO list...")
    outlines = gpd.read_file(gpkg)
    with open(ids, encoding="utf-8") as f:
        meta = pd.DataFrame(json.load(f))
    joined = outlines.merge(meta, left_on="PDOid", right_on="pdoid", how="inner")
    if joined.empty:
        sys.exit("No outline matched a PDO id: check the two files come from the same collection")
    joined = joined.to_crs("EPSG:4326").rename(columns={"pdoid": "pdo_id", "pdoname": "name"})
    for iso, group in joined.groupby("country"):
        path = os.path.join(GEO, f"{COUNTRIES.get(iso, iso.lower())}_pdo.parquet")
        group[[c for c in COLUMNS if c in group.columns]].to_parquet(path)
        print(f"{iso}: {len(group)} PDOs -> {os.path.basename(path)}")


if __name__ == "__main__":
    main()
