"""Builds data/geo/admin/admin_areas.geojson: outlines for appellations that are an administrative area (a Japanese
prefecture, a Swiss canton, an Italian IGT region, a French IGP's départements...), from Natural Earth's states and
provinces (public domain, the same file as build_region_outlines.py). The shape store reads it as source `admin`
(app/api/data/shape_sources.json), linked by country and appellation name. Full detail: build_shapes.py simplifies
for display. Rerun when AREAS changes, then build_shapes.py --only admin and the shape links:

    python geo_scripts/build_admin_areas.py [path to ne_10m_admin_1_states_provinces .zip or .shp]

Only areas that are the appellation (or its legal area) belong here, not a region that merely contains it: Central
Otago is drawn as Otago, its region, which is the one approximation, said in its note.
"""
import json
import os
import sys

import numpy as np
import shapely

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_region_outlines as regions  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "geo", "admin", "admin_areas.geojson")

# (country as on the region, appellation name as in the appellations table) -> areas, as in build_region_outlines:
# "iso:XX-YY", "it:<Italian region>", "country:<name>", plus "es:<Spanish region>"
AREAS = {
    # Japan: prefectures
    ("Japan", "Yamanashi-ken"): ["iso:JP-19"],
    ("Japan", "Hokkaido-ken"): ["iso:JP-01"],
    ("Japan", "Nagano-ken"): ["iso:JP-20"],
    # Switzerland: cantons
    ("Switzerland", "Graubünden"): ["iso:CH-GR"],
    ("Switzerland", "Neuchatel"): ["iso:CH-NE"],
    ("Switzerland", "Ticino"): ["iso:CH-TI"],
    ("Switzerland", "Valais"): ["iso:CH-VS"],
    # Italy: IGTs named after a region or provinces
    ("Italy", "Toscana"): ["it:Toscana"],
    ("Italy", "Terre Siciliane"): ["it:Sicily"],
    ("Italy", "Venezia Giulia"): ["it:Friuli-Venezia Giulia"],
    ("Italy", "Trentino-Alto Adige"): ["it:Trentino-Alto Adige"],
    ("Italy", "Umbria"): ["it:Umbria"],
    ("Italy", "Veneto"): ["it:Veneto"],
    ("Italy", "Puglia"): ["it:Apulia"],
    ("Italy", "Colli della Toscana"): ["iso:IT-FI", "iso:IT-SI", "iso:IT-AR", "iso:IT-PI", "iso:IT-PT", "iso:IT-PO"],
    ("Italy", "Pecorino Colli Aprutini"): ["iso:IT-TE"],
    # France: IGPs over whole départements
    ("France", "Vin de Pays du Vaucluse"): ["iso:FR-84"],
    ("France", "Vin de Pays de l'Ardeche"): ["iso:FR-07"],
    ("France", "Cotes Catalanes"): ["iso:FR-66"],
    ("France", "Vin de Pays des Allobroges"): ["iso:FR-73", "iso:FR-74"],
    ("France", "Vin de Pays du Languedoc"): ["iso:FR-11", "iso:FR-30", "iso:FR-34", "iso:FR-66", "iso:FR-48"],
    # Spain: Vinos de la Tierra over a region or province
    ("Spain", "Castilla y León"): ["es:Castilla y León"],
    ("Spain", "Cádiz"): ["iso:ES-CA"],
    # Elsewhere
    ("Argentina", "Mendoza"): ["iso:AR-M"],
    ("Argentina", "Salta"): ["iso:AR-A"],
    ("Argentina", "Patagonia"): ["iso:AR-Q", "iso:AR-R", "iso:AR-L", "iso:AR-U"],
    ("Austria", "Styria"): ["iso:AT-6"],
    ("New Zealand", "Canterbury"): ["iso:NZ-CAN"],
    ("New Zealand", "Marlborough Valley"): ["iso:NZ-MBH"],
    ("New Zealand", "Central Otago"): ["iso:NZ-OTA"],  # approximation: the Otago region
    ("New Zealand", "North Otago"): ["iso:NZ-OTA"],  # approximation: the Otago region
    ("Lebanon", "Bekaa Valley"): ["iso:LB-BI"],
    ("Portugal", "Azores"): ["iso:PT-20"],
    ("United Kingdom", "Hampshire"): ["iso:GB-HAM"],
    ("United States", "California"): ["iso:US-CA"],
}
NOTES = {("New Zealand", "Central Otago"): "drawn as the Otago region", ("New Zealand", "North Otago"): "drawn as the Otago region"}


def pick(ne, spec):
    if spec.startswith("es:"):
        rows = ne[(ne.admin == "Spain") & (ne.region == spec[3:])]
        if rows.empty:
            raise SystemExit(f"Nothing in Natural Earth for {spec!r}")
        return list(rows.geometry)
    return regions.pick(ne, spec)


def main():
    ne = regions.load(sys.argv[1] if len(sys.argv) > 1 else None)
    features = []
    for (country, name), specs in AREAS.items():
        merged = shapely.union_all(shapely.make_valid(np.array([g for s in specs for g in pick(ne, s)], dtype=object)))
        features.append({"type": "Feature",
                         "properties": {"id": f"{country}:{name}", "name": name, "country": country, "areas": specs,
                                        "note": NOTES.get((country, name))},
                         "geometry": json.loads(shapely.to_geojson(merged))})
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "attribution": "Natural Earth (public domain)", "features": features},
                  f, ensure_ascii=False)
    print(f"{len(features)} areas, {os.path.getsize(OUT) // 1024} KB -> {os.path.normpath(OUT)}")


if __name__ == "__main__":
    main()
