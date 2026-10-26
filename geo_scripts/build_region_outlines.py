"""Builds app/api/data/region_outlines.geojson: one coarse outline per wine region, for the map's overview.

Wine regions are approximated by administrative areas from Natural Earth (public domain,
https://www.naturalearthdata.com): French departements, Italian and Spanish provinces, US and
Australian states, or a whole country. Where a wine region isn't an administrative area (Germany's
Anbaugebiete, Portugal's DOC regions), by its appellations' outlines from the shape store
(data/geo/shapes/, built by build_shapes.py). The app only reads the file; rerun this when a region is
added or REGIONS below changes:

    python geo_scripts/build_region_outlines.py [path to ne_10m_admin_1_states_provinces .zip or .shp]

Without a path, the Natural Earth file is downloaded (~15 MB). A region in COLORS has that colour in
the file: a new region took it when it was created (docs/reference-data.md).
"""
import json
import os
import sys
import tempfile
import urllib.request

import geopandas as gpd
import numpy as np
import shapely

NE_URL = "https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_1_states_provinces.zip"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app", "api", "data", "region_outlines.geojson")
SHAPES_DIR = os.getenv("SHAPES_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "geo", "shapes"))

# Region name (as in the regions table) -> what it covers:
#   "iso:XX-YY"       an ISO 3166-2 area (French departement, Spanish or Italian province, US state...)
#   "it:<region>"     every Italian province of an Italian region (Natural Earth's names: Apulia, Sicily)
#   "uk:<nation>"     England, Scotland, Wales or Northern Ireland
#   "country:<name>"  a whole country (Natural Earth's `admin` name)
#   "...@w,s,e,n"     any of these clipped to a box (France without its overseas departments)
#   "shape:<source>:<id>"  a shape of the shape store, an appellation's outline ("shape:eu:PDO-DE-A1270", Mosel)
# Several regions can overlap (Italy contains Piemonte): the map draws the smaller ones on top.
REGIONS = {
    # France, by departement
    "Alsace": ["iso:FR-67", "iso:FR-68"],
    "Beaujolais": ["iso:FR-69"],
    "Bordeaux": ["iso:FR-33"],
    "Bourgogne": ["iso:FR-89", "iso:FR-21", "iso:FR-71"],
    "Champagne": ["iso:FR-51", "iso:FR-10"],
    "Charentes": ["iso:FR-16", "iso:FR-17"],
    "Corsica": ["iso:FR-2A", "iso:FR-2B"],
    "Jura": ["iso:FR-39"],
    "Languedoc": ["iso:FR-30", "iso:FR-34", "iso:FR-11", "iso:FR-66"],
    "Limousin": ["iso:FR-19"],
    "Loire": ["iso:FR-44", "iso:FR-49", "iso:FR-37", "iso:FR-41", "iso:FR-18", "iso:FR-58"],
    "Lorraine": ["iso:FR-54", "iso:FR-57"],
    "Lyonnais": ["iso:FR-69"],
    "Provence": ["iso:FR-13", "iso:FR-83", "iso:FR-06"],
    "Rhone": ["iso:FR-26", "iso:FR-07", "iso:FR-84"],
    "Savoie": ["iso:FR-73", "iso:FR-74"],
    "France": ["country:France@-5.5,41,10,51.5"],  # metropolitan France and Corsica
    "Sud-Ouest": ["iso:FR-24", "iso:FR-47", "iso:FR-46", "iso:FR-82", "iso:FR-81", "iso:FR-32",
                  "iso:FR-40", "iso:FR-64", "iso:FR-65", "iso:FR-31"],  # South West France, in French
    # Italy
    "Italy": ["country:Italy"],
    "Valle d'Aosta": ["it:Valle d'Aosta"],
    "Piemonte": ["it:Piemonte"],
    "Lombardia": ["it:Lombardia"],
    "Trentino-Alto Adige": ["it:Trentino-Alto Adige"],
    "Veneto": ["it:Veneto"],
    "Friuli-Venezia Giulia": ["it:Friuli-Venezia Giulia"],
    "Liguria": ["it:Liguria"],
    "Emilia-Romagna": ["it:Emilia-Romagna"],
    "Toscana": ["it:Toscana"],
    "Umbria": ["it:Umbria"],
    "Marche": ["it:Marche"],
    "Lazio": ["it:Lazio"],
    "Abruzzo": ["it:Abruzzo"],
    "Molise": ["it:Molise"],
    "Campania": ["it:Campania"],
    "Puglia": ["it:Apulia"],
    "Basilicata": ["it:Basilicata"],
    "Calabria": ["it:Calabria"],
    "Sicilia": ["it:Sicily"],
    "Sardegna": ["it:Sardegna"],
    # Spain: the classic wine zones, by province
    "España Verde": ["iso:ES-C", "iso:ES-LU", "iso:ES-OR", "iso:ES-PO", "iso:ES-O", "iso:ES-S", "iso:ES-BI", "iso:ES-SS"],
    "Castilla y León": ["iso:ES-AV", "iso:ES-BU", "iso:ES-LE", "iso:ES-P", "iso:ES-SA", "iso:ES-SG", "iso:ES-SO",
                        "iso:ES-VA", "iso:ES-ZA"],
    "Alto Ebro": ["iso:ES-LO", "iso:ES-NA", "iso:ES-VI"],
    "Aragón": ["iso:ES-HU", "iso:ES-TE", "iso:ES-Z"],
    "Catalunya": ["iso:ES-B", "iso:ES-GI", "iso:ES-L", "iso:ES-T"],
    "Levante": ["iso:ES-V", "iso:ES-A", "iso:ES-CS", "iso:ES-MU"],
    "Castilla-La Mancha y Madrid": ["iso:ES-AB", "iso:ES-CR", "iso:ES-CU", "iso:ES-GU", "iso:ES-TO", "iso:ES-M"],
    "Extremadura": ["iso:ES-BA", "iso:ES-CC"],
    "Andalucía": ["iso:ES-AL", "iso:ES-CA", "iso:ES-CO", "iso:ES-GR", "iso:ES-H", "iso:ES-J", "iso:ES-MA", "iso:ES-SE"],
    "Islas Baleares": ["iso:ES-PM"],
    "Islas Canarias": ["iso:ES-GC", "iso:ES-TF"],
    # Germany: the 13 Anbaugebiete, by their EU PDO outlines
    "Ahr": ["shape:eu:PDO-DE-A0867"],
    "Baden": ["shape:eu:PDO-DE-A1264"],
    "Franken": ["shape:eu:PDO-DE-A1267"],
    "Hessische Bergstraße": ["shape:eu:PDO-DE-A1268"],
    "Mittelrhein": ["shape:eu:PDO-DE-A1269"],
    "Mosel": ["shape:eu:PDO-DE-A1270"],
    "Nahe": ["shape:eu:PDO-DE-A1271"],
    "Pfalz": ["shape:eu:PDO-DE-A1272"],
    "Rheingau": ["shape:eu:PDO-DE-A1273"],
    "Rheinhessen": ["shape:eu:PDO-DE-A1274"],
    "Saale-Unstrut": ["shape:eu:PDO-DE-A1275"],
    "Sachsen": ["shape:eu:PDO-DE-A1277"],
    "Württemberg": ["shape:eu:PDO-DE-A1276"],
    # Portugal: the wine regions, by their DOCs' outlines (Douro with Porto, Lisboa's eight DOCs...)
    "Vinho Verde": ["shape:eu:PDO-PT-A1545"],
    "Trás-os-Montes": ["shape:eu:PDO-PT-A1466"],
    "Douro": ["shape:eu:PDO-PT-A1539", "shape:eu:PDO-PT-A1540"],
    "Dão": ["shape:eu:PDO-PT-A1534"],
    "Bairrada": ["shape:eu:PDO-PT-A1537"],
    "Beira Interior": ["shape:eu:PDO-PT-A1546"],
    "Lisboa": ["shape:eu:PDO-PT-A1461", "shape:eu:PDO-PT-A1462", "shape:eu:PDO-PT-A1463", "shape:eu:PDO-PT-A1465",
               "shape:eu:PDO-PT-A1468", "shape:eu:PDO-PT-A1469", "shape:eu:PDO-PT-A1470", "shape:eu:PDO-PT-A1471"],
    "Tejo": ["shape:eu:PDO-PT-A1544"],
    "Península de Setúbal": ["shape:eu:PDO-PT-A1457", "shape:eu:PDO-PT-A1460"],
    "Alentejo": ["shape:eu:PDO-PT-A1542"],
    "Algarve": ["shape:eu:PDO-PT-A1449", "shape:eu:PDO-PT-A1450", "shape:eu:PDO-PT-A1452", "shape:eu:PDO-PT-A1454"],
    "Madeira": ["shape:eu:PDO-PT-A0038", "shape:eu:PDO-PT-A0039"],
    "Açores": ["shape:eu:PDO-PT-A1444", "shape:eu:PDO-PT-A1445", "shape:eu:PDO-PT-A1446"],
    # Austria: the wine-growing states
    "Niederösterreich": ["iso:AT-3"],
    "Burgenland": ["iso:AT-1"],
    "Steiermark": ["iso:AT-6"],
    "Wien": ["iso:AT-9"],
    # Australia: the states (GI zones over several states stay in Australia)
    "South Australia": ["iso:AU-SA"],
    "Victoria": ["iso:AU-VIC"],
    "New South Wales": ["iso:AU-NSW"],
    "Western Australia": ["iso:AU-WA"],
    "Tasmania": ["iso:AU-TAS"],
    "Queensland": ["iso:AU-QLD"],
    # Americas
    "Argentina": ["country:Argentina"],
    "Mendoza": ["iso:AR-M"],
    "California": ["iso:US-CA"],
    "Pacific Northwest": ["iso:US-WA", "iso:US-OR"],
    "New York": ["iso:US-NY"],
    "Virginia": ["iso:US-VA"],
    "Texas": ["iso:US-TX"],
    "Michigan": ["iso:US-MI"],
    "Ohio": ["iso:US-OH"],
    "Pennsylvania": ["iso:US-PA"],
    "Missouri": ["iso:US-MO"],
    "United States": ["country:United States of America"],
    "Canada": ["country:Canada"],
    "Chile": ["country:Chile"],
    # United Kingdom
    "England": ["uk:England"],
    "United Kingdom": ["country:United Kingdom"],
    # Whole countries
    "Australia": ["country:Australia"],
    "Austria": ["country:Austria"],
    "Belgium": ["country:Belgium"],
    "Bulgaria": ["country:Bulgaria"],
    "China": ["country:China"],
    "Croatia": ["country:Croatia"],
    "Cyprus": ["country:Cyprus"],
    "Czech Republic": ["country:Czech Republic"],
    "Denmark": ["country:Denmark"],
    "Georgia": ["country:Georgia"],
    "Germany": ["country:Germany"],
    "Greece": ["country:Greece"],
    "Hungary": ["country:Hungary"],
    "Japan": ["country:Japan"],
    "Lebanon": ["country:Lebanon"],
    "Luxembourg": ["country:Luxembourg"],
    "Malta": ["country:Malta"],
    "Netherlands": ["country:Netherlands"],
    "New Zealand": ["country:New Zealand"],
    "Portugal": ["country:Portugal"],
    "Romania": ["country:Romania"],
    "Slovakia": ["country:Slovakia"],
    "Slovenia": ["country:Slovenia"],
    "South Africa": ["country:South Africa"],
    "Spain": ["country:Spain"],
    "Switzerland": ["country:Switzerland"],
}

# The new regions' colours: shades of their country's current colour (the country-level region's), lighter or
# darker, neighbours told apart. The existing regions keep theirs (Piemonte, Toscana: in the regions table).
# Portugal shares Spain's pale yellow: its regions are a little warmer.
SHADES = [
    ("#ea9999", ["Valle d'Aosta", "Lombardia", "Trentino-Alto Adige", "Veneto", "Friuli-Venezia Giulia", "Liguria",
                 "Emilia-Romagna", "Umbria", "Marche", "Lazio", "Abruzzo", "Molise", "Campania", "Puglia",
                 "Basilicata", "Calabria", "Sicilia", "Sardegna"]),
    ("#fff2cc", ["España Verde", "Castilla y León", "Alto Ebro", "Aragón", "Catalunya", "Levante",
                 "Castilla-La Mancha y Madrid", "Extremadura", "Andalucía", "Islas Baleares", "Islas Canarias"]),
    ("#ffe8c2", ["Vinho Verde", "Trás-os-Montes", "Douro", "Dão", "Bairrada", "Beira Interior", "Lisboa", "Tejo",
                 "Península de Setúbal", "Alentejo", "Algarve", "Madeira", "Açores"]),
    ("#a2c4c9", ["Ahr", "Mosel", "Mittelrhein", "Nahe", "Rheingau", "Rheinhessen", "Pfalz", "Hessische Bergstraße",
                 "Franken", "Württemberg", "Baden", "Saale-Unstrut", "Sachsen"]),
    ("#d0e0e3", ["Niederösterreich", "Wien", "Burgenland", "Steiermark"]),
    ("#f1c232", ["Western Australia", "South Australia", "Victoria", "Tasmania", "New South Wales", "Queensland"]),
    ("#f6b26b", ["New York", "Pennsylvania", "Ohio", "Michigan", "Missouri", "Texas", "Virginia"]),
]
# How far the shades go from the country's colour (HSL lightness), and how dark or light they may get
SHADE_SPREAD = 0.16
SHADE_RANGE = (0.42, 0.9)


def shades(base, names):
    """{name: colour}: as many lightness steps around the base as names, in an order that puts far-apart steps
    next to each other (the names are listed roughly as neighbours)."""
    import colorsys
    r, g, b = (int(base[i:i + 2], 16) / 255 for i in (1, 3, 5))
    h, light, s = colorsys.rgb_to_hls(r, g, b)
    low, high = max(SHADE_RANGE[0], light - SHADE_SPREAD), min(SHADE_RANGE[1], light + SHADE_SPREAD)
    if high - low < SHADE_SPREAD:  # a very pale colour (Spain's) only has room to go darker
        low = max(SHADE_RANGE[0], high - 2 * SHADE_SPREAD)
    n = len(names)
    steps = [low + (high - low) * i / max(1, n - 1) for i in range(n)]
    order = [steps[i] for pair in zip(range(0, n, 2), range(n - 1 - (n % 2 == 0), 0, -2)) for i in pair]
    order += [s_ for s_ in steps if s_ not in order]
    out = {}
    for name, level in zip(names, order):
        rr, gg, bb = colorsys.hls_to_rgb(h, level, max(s, 0.35))
        out[name] = "#" + "".join(f"{round(c * 255):02x}" for c in (rr, gg, bb))
    return out


COLORS = {name: colour for base, names in SHADES for name, colour in shades(base, names).items()}
COLORS["France"] = "#d9d2e9"  # a new country-level region: Vin de France's

# Simplification relative to the outline's size (1/400 of its diagonal), never finer than ~1 km
RELATIVE_TOLERANCE = 1 / 400
MIN_TOLERANCE = 0.01
DIGITS = 3
# A store shape's parts closer than about twice this (degrees, ~3 km) are joined
STORE_GAP = 0.03
# Islands and enclaves smaller than this share of the outline's biggest part are dropped
MIN_PART_SHARE = 0.01


def load(source):
    if source is None:
        tmp = os.path.join(tempfile.gettempdir(), os.path.basename(NE_URL))
        if not os.path.exists(tmp):
            print(f"Downloading {NE_URL}")
            urllib.request.urlretrieve(NE_URL, tmp)
        source = tmp
    path = f"zip://{source}" if source.endswith(".zip") else source
    return gpd.read_file(path, columns=["admin", "iso_3166_2", "region", "geonunit"])


_store = {}


def store_shape(source, sid):
    """A shape of the shape store (its full geometry), by source and id."""
    if source not in _store:
        import pyarrow.parquet as pq
        path = os.path.join(SHAPES_DIR, f"{source}.parquet")
        if not os.path.exists(path):
            raise SystemExit(f"No shape store file {path}: build it first (geo_scripts/build_shapes.py)")
        t = pq.read_table(path, columns=["source_id", "geometry"]).to_pydict()
        _store[source] = dict(zip(t["source_id"], t["geometry"]))
    wkb = _store[source].get(sid)
    if wkb is None:
        raise SystemExit(f"No shape {sid!r} in the {source} store")
    return shapely.from_wkb(wkb)


def pick(ne, spec):
    if "@" in spec:
        spec, box = spec.split("@", 1)
        clip = shapely.box(*map(float, box.split(",")))
        return [g.intersection(clip) for g in pick(ne, spec) if g.intersects(clip)]
    kind, value = spec.split(":", 1)
    if kind == "shape":  # vineyards in strips along the valleys: gaps closed so the region reads as one area
        shape = shapely.make_valid(store_shape(*value.split(":", 1)))
        return [shape.buffer(STORE_GAP, quad_segs=4).buffer(-STORE_GAP, quad_segs=4)]
    column = {"iso": "iso_3166_2", "country": "admin", "uk": "geonunit"}.get(kind)
    rows = ne[(ne.admin == "Italy") & (ne.region == value)] if kind == "it" else ne[ne[column] == value]
    if rows.empty:
        raise SystemExit(f"Nothing in Natural Earth for {spec!r}")
    return list(rows.geometry)


def outline(geoms):
    merged = shapely.union_all(shapely.make_valid(np.array(geoms, dtype=object)))
    parts = [p for p in shapely.get_parts(merged) if p.geom_type == "Polygon"]
    biggest = max(p.area for p in parts)
    parts = [shapely.Polygon(p.exterior) for p in parts if p.area >= biggest * MIN_PART_SHARE]
    shape = shapely.MultiPolygon(parts) if len(parts) > 1 else parts[0]
    w, s, e, n = shape.bounds
    tolerance = max(MIN_TOLERANCE, np.hypot(e - w, n - s) * RELATIVE_TOLERANCE)
    return shapely.transform(shapely.simplify(shape, tolerance, preserve_topology=True), lambda c: np.round(c, DIGITS))


def main():
    ne = load(sys.argv[1] if len(sys.argv) > 1 else None)
    features = []
    for name, specs in REGIONS.items():
        shape = outline([g for spec in specs for g in pick(ne, spec)])
        features.append({
            "type": "Feature",
            "properties": {"name": name, "source": specs, "bbox": [round(b, DIGITS) for b in shape.bounds],
                           **({"color": COLORS[name]} if name in COLORS else {})},
            "geometry": json.loads(shapely.to_geojson(shape)),
        })
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": features,
                   "attribution": "Natural Earth (public domain); EU geographical indications' outlines (eAmbrosia)"},
                  f, ensure_ascii=False, separators=(",", ":"))
    points = sum(int(shapely.get_num_coordinates(shapely.from_geojson(json.dumps(f["geometry"])))) for f in features)
    print(f"{len(features)} regions, {points} points, {os.path.getsize(OUT) // 1024} KB -> {os.path.normpath(OUT)}")


if __name__ == "__main__":
    main()
