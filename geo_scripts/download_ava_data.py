"""Downloads the US American Viticultural Areas from UC Davis Library's AVA project (github.com/UCDavisLibrary/ava,
CC0) into data/geo/us_avas_combined.parquet, the file the shape store's `ava` source reads.

    python geo_scripts/download_ava_data.py          # then build_shapes.py --only ava and the shape links

One GeoJSON file per AVA, listed through GitHub's API (unauthenticated: 60 requests an hour, one is used).
"""
import json
import os
import urllib.request

import geopandas as gpd
import pandas as pd

GEO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "geo")
LISTING = "https://api.github.com/repos/UCDavisLibrary/ava/contents/avas"


def main():
    with urllib.request.urlopen(LISTING, timeout=60) as r:
        files = [f["download_url"] for f in json.load(r) if f["name"].endswith(".geojson")]
    print(f"{len(files)} AVAs to download...")
    frames = [gpd.read_file(url) for url in files]
    out = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs=frames[0].crs)
    path = os.path.join(GEO, "us_avas_combined.parquet")
    os.makedirs(GEO, exist_ok=True)
    out.to_parquet(path)
    print(f"{len(out)} AVAs -> {os.path.normpath(path)}")


if __name__ == "__main__":
    main()
