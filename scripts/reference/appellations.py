"""The missing appellations (docs/reference-data.md: how the reference data was built, and how to refresh it).

Adds what the official lists have and the database doesn't, under the right region:
- France: every name of INAO's parcel delimitation (data/geo/inao_denoms/: appellations and complementary geographic
  names; the premier cru climats are vineyards already) and every wine AOC and IGP of its geographic areas
  (data/geo/inao_aires/); a complementary name under its appellation's region, the others by outline;
- United States: every AVA of the shape store (UC Davis), by outline among the states that are regions;
- the EU register (eAmbrosia, data/geo/eambrosia/): every registered wine PDO and PGI, a PDO by its outline (the eu
  store), a PGI by its name (a Landwein's Anbaugebiet, a Vinho Regional's region, an IGT named after its province);
  Greek names in Latin letters (the Greek one an alias); a country without a region gets its country-level one;
- other countries' official lists, one CSV each in app/api/data/registers/ (name, aliases, type, within, region;
  its sources beside it): South Africa's Wine of Origin units, New Zealand's GIs, Chile's DO zoning, Argentina's IGs
  and DOCs, Canada's VQA and BC areas, Switzerland's AOCs, Georgia's, Japan's... under the region a row or one of
  the units it's within is named after (Mendoza), else the country; an existing row without a type gets the list's;
  a row's note goes into its details (after the classification, details.py);
- each country's generic, national appellation (Vino d'Italia, Deutscher Wein...), under the country.
A name is already there when any of its forms is ("X ou Y", "X / Y", with or without "Grand Cru"), as a name or an
alias in the same country, or when its outline is already linked. New rows get their outline link (boundary) at once.

A dry run unless --commit; the report goes to data/reference_build/appellations.txt. Rerunning is safe: what's there stays.

    python scripts/reference/appellations.py            # dry run
    python scripts/reference/appellations.py --commit   # after a backup
"""
import argparse
import collections
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "app", "api"))

GEO = os.getenv("GEO_DIR", os.path.join(ROOT, "data", "geo"))
OUTLINES = os.path.join(ROOT, "app", "api", "data", "region_outlines.geojson")
SHAPES_DIR = os.getenv("SHAPES_DIR", os.path.join(GEO, "shapes"))
# The share of an outline a region must hold to take it
CONTAINED = 0.8
REPORT = os.path.join(ROOT, "data", "reference_build", "appellations.txt")

# Each country's own generic appellation, under the country-level region (Vin de France, Vinho de Portugal and
# Landwein are there already)
NATIONAL = {"Vino d'Italia": "Italy", "Vino de España": "Spain", "Deutscher Wein": "Germany",
            "Österreichischer Wein": "Austria"}
# Existing rows renamed to the official spelling (the old name stays an alias)
RENAMES = {"Vino de Espana": "Vino de España"}
# INAO's wine categories, and the signs that are wine appellations (IG: spirits; PNT: not a wine)
WINE = re.compile(r"\bVins?\b")
SIGNS = {"AOC": "AOP", "AOP": "AOP", "IGP": "IGP"}


def outlines():
    """{region name: (shape, colour or None)} from the region outlines file."""
    import json
    import shapely
    with open(OUTLINES, encoding="utf-8") as f:
        data = json.load(f)
    return {feat["properties"]["name"]: (shapely.make_valid(shapely.from_geojson(json.dumps(feat["geometry"]))),
                                         feat["properties"].get("color")) for feat in data["features"]}


_store = {}


def store_shape(boundary):
    """The display outline of a "source:id" link, or None."""
    import shapely
    if not boundary or ":" not in boundary:
        return None
    source, sid = boundary.split(":", 1)
    if source not in _store:
        import pyarrow.parquet as pq
        path = os.path.join(SHAPES_DIR, f"{source}.parquet")
        t = pq.read_table(path, columns=["source_id", "display"]).to_pydict() if os.path.exists(path) else {}
        _store[source] = dict(zip(t.get("source_id", []), t.get("display", [])))
    wkb = _store[source].get(sid)
    return shapely.make_valid(shapely.from_wkb(wkb)) if wkb else None


def place(shape, candidates):
    """(region name or None, why): the candidate holding CONTAINED of the shape; else None and the shares."""
    if shape is None or shape.is_empty or not shape.area:
        return None, "no outline"
    shares = sorted(((shape.intersection(g).area / shape.area, name) for name, g in candidates.items()
                     if g.intersects(shape)), reverse=True)
    if shares and shares[0][0] >= CONTAINED:
        return shares[0][1], f"{shares[0][0]:.0%}"
    spread = ", ".join(f"{n} {s:.0%}" for s, n in shares[:3] if s >= 0.05) or "outside every region"
    return None, spread


# The EU register's wine names, downloaded on the PC: POST the filter (product type 1, wine) to
# EAMBROSIA_API with rows=5000 into data/geo/eambrosia/wine_gis.json (eu_register() does it when the file is missing)
EAMBROSIA_API = "https://ec.europa.eu/geographical-indications-register/eambrosia-public-api/api/gi-applications/filter"
EAMBROSIA_PAGE = "https://ec.europa.eu/agriculture/eambrosia/geographical-indications-register/details/"
EU_COUNTRIES = {"Czechia": "Czech Republic"}
REGISTERS = os.path.join(ROOT, "app", "api", "data", "registers")
# A register file's country (the file name, south_africa.csv)
REGISTER_COUNTRIES = {"south_africa": "South Africa", "new_zealand": "New Zealand", "chile": "Chile",
                      "argentina": "Argentina", "canada": "Canada", "switzerland": "Switzerland", "georgia": "Georgia",
                      "japan": "Japan", "uruguay": "Uruguay"}
# What a PDO / PGI is called in each country (else "PDO" / "PGI")
PDO_TYPES = {"France": "AOP", "Portugal": "DOC"}
PGI_TYPES = {"France": "IGP", "Italy": "IGT", "Spain": "VT", "Germany": "Landwein", "Austria": "Landwein",
             "Portugal": "Vinho Regional"}
# Where a GI without an outline is, by its name (the register says the country only): Italy's IGTs, Spain's
# Vinos de Pago, Germany's Landweins... Those over several regions (Alto Livenza, Trevenezie, Vallagarina, Landwein
# Rhein) aren't listed: they stay in the country.
PLACES = {
    # Italy
    "Allerona": "Umbria", "Alpi Retiche": "Lombardia", "Alta Valle della Greve": "Toscana", "Alto Mincio": "Lombardia",
    "Anagni": "Lazio", "Arghillà": "Calabria", "Avola": "Sicilia", "Barbagia": "Sardegna",
    "Benaco Bresciano": "Lombardia", "Bergamasca": "Lombardia", "Bettona": "Umbria",
    "Bianco del Sillaro": "Emilia-Romagna", "Camarro": "Sicilia", "Cannara": "Umbria",
    "Castelfranco Emilia": "Emilia-Romagna", "Catalanesca del Monte Somma": "Campania",
    "Civitella d'Agliano": "Lazio", "Colli Cimini": "Lazio", "Colli Trevigiani": "Veneto",
    "Colli del Limbara": "Sardegna", "Colli della Toscana centrale": "Toscana", "Colli di Salerno": "Campania",
    "Collina del Milanese": "Lombardia", "Colline Savonesi": "Liguria", "Colline del Genovesato": "Liguria",
    "Conselvano": "Veneto", "Costa Etrusco Romana": "Lazio", "Costa Toscana": "Toscana", "Costa Viola": "Calabria",
    "Daunia": "Puglia", "Dugenta": "Campania", "Epomeo": "Campania", "Fontanarossa di Cerda": "Sicilia",
    "Forlì": "Emilia-Romagna", "Fortana del Taro": "Emilia-Romagna", "Frusinate": "Lazio",
    "Isola dei Nuraghi": "Sardegna", "Liguria di Levante": "Liguria", "Lipuda": "Calabria", "Locride": "Calabria",
    "Marca Trevigiana": "Veneto", "Marmilla": "Sardegna", "Mitterberg": "Trentino-Alto Adige",
    "Montecastelli": "Toscana", "Montenetto di Brescia": "Lombardia", "Murgia": "Puglia", "Narni": "Umbria",
    "Nurra": "Sardegna", "Osco": "Molise", "Paestum": "Campania", "Palizzi": "Calabria", "Parteolla": "Sardegna",
    "Pellaro": "Calabria", "Planargia": "Sardegna", "Pompeiano": "Campania", "Provincia di Mantova": "Lombardia",
    "Provincia di Nuoro": "Sardegna", "Provincia di Pavia": "Lombardia", "Quistello": "Lombardia",
    "Roccamonfina": "Campania", "Romangia": "Sardegna", "Ronchi Varesini": "Lombardia",
    "Ronchi di Brescia": "Lombardia", "Rotae": "Molise", "Rubicone": "Emilia-Romagna", "Sabbioneta": "Lombardia",
    "Salento": "Puglia", "Salina": "Sicilia", "Scilla": "Calabria", "Sebino": "Lombardia", "Sibiola": "Sardegna",
    "Spello": "Umbria", "Tarantino": "Puglia", "Terrazze dell'Imperiese": "Liguria", "Terre Abruzzesi": "Abruzzo",
    "Terre Aquilane": "Abruzzo", "Terre Lariane": "Lombardia", "Terre del Volturno": "Campania",
    "Terre di Veleja": "Emilia-Romagna", "Tharros": "Sardegna", "Trexenta": "Sardegna",
    "Val Tidone": "Emilia-Romagna", "Val di Magra": "Toscana", "Val di Neto": "Calabria", "Valcamonica": "Lombardia",
    "Valdamato": "Calabria", "Valle Belice": "Sicilia", "Valle d'Itria": "Puglia", "Valle del Tirso": "Sardegna",
    "Valli di Porto Pino": "Sardegna", "Veneto Orientale": "Veneto", "Vigneti delle Dolomiti": "Trentino-Alto Adige",
    "dell'Emilia": "Emilia-Romagna", "Canelli": "Piemonte", "Casauria": "Abruzzo", "Cirò Classico": "Calabria",
    # Spain's Vinos de Pago and the rest
    "Abadía Retuerta": "Castilla y León", "Bolandin": "Alto Ebro", "Campo de Calatrava": "Castilla-La Mancha y Madrid",
    "Tharsys": "Levante", "Urbezo": "Aragón", "Terras do Navia": "España Verde",
    # Germany's Landweins
    "Ahrtaler Landwein": "Ahr", "Badischer Landwein": "Baden", "Landwein Oberrhein": "Baden",
    "Taubertäler Landwein": "Baden", "Bayerischer Bodensee-Landwein": "Franken", "Landwein Main": "Franken",
    "Landwein der Mosel": "Mosel", "Landwein der Ruwer": "Mosel", "Landwein der Saar": "Mosel",
    "Saarländischer Landwein": "Mosel", "Nahegauer Landwein": "Nahe", "Pfälzer Landwein": "Pfalz",
    "Rheingauer Landwein": "Rheingau", "Rheinischer Landwein": "Rheinhessen", "Rheinburgen-Landwein": "Mittelrhein",
    "Mitteldeutscher Landwein": "Saale-Unstrut", "Sächsischer Landwein": "Sachsen",
    "Schwäbischer Landwein": "Württemberg", "Landwein Neckar": "Württemberg",
    "Starkenburger Landwein": "Hessische Bergstraße",
    # Austria, the United Kingdom
    "Steirerland": "Steiermark", "Ruster Ausbruch": "Burgenland", "Rosalia": "Burgenland",
    "Sussex": "England", "English Regional": "England",
}
# The register's spelling of a name the database has spelled otherwise: it's that one
SAME = {"Valle del Miño-Ourense": "Valle del Miño-Orense"}
# A PGI without an outline and not in PLACES, by a word of its name (else a province's or region's name)
KEYWORDS = {
    "Portugal": [("minho", "Vinho Verde"), ("transmontano", "Trás-os-Montes"), ("duriense", "Douro"),
                 ("terras do dao", "Dão"), ("beira atlantico", "Bairrada"), ("terras da beira", "Beira Interior"),
                 ("lisboa", "Lisboa"), ("tejo", "Tejo"), ("setubal", "Península de Setúbal"), ("alentejano", "Alentejo"),
                 ("algarve", "Algarve"), ("madeirense", "Madeira"), ("acores", "Açores")],
    "Austria": [("steirerland", "Steiermark")],
}
LATIN = re.compile(r"[\u0000-\u024f\u1e00-\u1eff\u2019\s.-]+")
GREEK = {"α": "a", "β": "v", "γ": "g", "δ": "d", "ε": "e", "ζ": "z", "η": "i", "θ": "th", "ι": "i", "κ": "k", "λ": "l",
         "μ": "m", "ν": "n", "ξ": "x", "ο": "o", "π": "p", "ρ": "r", "σ": "s", "ς": "s", "τ": "t", "υ": "y", "φ": "f",
         "χ": "ch", "ψ": "ps", "ω": "o"}
GREEK_PAIRS = [("ου", "ou"), ("αι", "ai"), ("ει", "ei"), ("οι", "oi"), ("αυ", "av"), ("ευ", "ev"), ("γγ", "ng"),
               ("γκ", "gk"), ("μπ", "mp"), ("ντ", "nt")]


def latin_name(name):
    """A Greek name in Latin letters (ELOT 743, simplified: Άβδηρα -> Avdira), a Cyrillic one transliterated; a
    Latin one as it is."""
    import unicodedata
    if not re.search(r"[Ͱ-ϿЀ-ӿ]", name):
        return name
    if re.search(r"[Ѐ-ӿ]", name):
        from unidecode import unidecode
        return unidecode(name)
    plain = "".join(c for c in unicodedata.normalize("NFD", name) if not unicodedata.combining(c))
    out, i = [], 0
    while i < len(plain):
        low = plain[i].lower()
        pair = plain[i:i + 2].lower()
        hit = next((lat for gr, lat in GREEK_PAIRS if pair == gr), None)
        if hit:
            chunk, i = hit, i + 2
        else:
            chunk, i = GREEK.get(low, plain[i]), i + 1
        out.append(chunk.capitalize() if plain[i - (2 if hit else 1)].isupper() else chunk)
    return "".join(out)


def eu_register():
    """The registered wine GIs of the EU register (the downloaded file; fetched when it's missing)."""
    import json
    path = os.path.join(GEO, "eambrosia", "wine_gis.json")
    if not os.path.exists(path):
        import urllib.request
        body = json.dumps({"cnCode": [], "filters": [{"fieldName": "qualityProductTypeId", "fieldValue": ["1"]}],
                           "first": 0, "lang": "en", "sortField": "protectedName", "sortOrder": 1, "rows": 5000,
                           "registerId": None, "cnCodes": []}).encode()
        req = urllib.request.Request(EAMBROSIA_API, data=body, headers={"Content-Type": "application/json"})
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with urllib.request.urlopen(req, timeout=120) as r, open(path, "wb") as f:
            f.write(r.read())
    with open(path, encoding="utf-8") as f:
        return [g for g in json.load(f)["results"] if g.get("status") == "Registered"]


def province_regions():
    """{(country, name form): region}: Italy's and Spain's provinces and regions (Natural Earth), for a PGI named
    after one (Benevento, Basilicata)."""
    import importlib.util
    import tempfile
    import geopandas as gpd
    spec = importlib.util.spec_from_file_location("outlines", os.path.join(ROOT, "geo_scripts", "build_region_outlines.py"))
    build = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build)
    source = os.path.join(tempfile.gettempdir(), os.path.basename(build.NE_URL))
    if not os.path.exists(source):
        build.load(None)  # downloads it there
    named = gpd.read_file(f"zip://{source}", columns=["admin", "iso_3166_2", "name", "region"], ignore_geometry=True)
    iso_region = {spec_[4:]: region for region, specs in build.REGIONS.items() for spec_ in specs if spec_.startswith("iso:ES-")}
    it_region = {spec_[3:]: region for region, specs in build.REGIONS.items() for spec_ in specs if spec_.startswith("it:")}
    out = {}
    for r in named.itertuples():
        if r.admin == "Italy" and r.region in it_region:
            region = it_region[r.region]
            for k in forms(r.name) | forms(r.region) | forms(region):
                out.setdefault(("Italy", k), region)
        elif r.admin == "Spain" and r.iso_3166_2 in iso_region:
            for k in forms(r.name):
                out.setdefault(("Spain", k), iso_region[r.iso_3166_2])
    return out


def by_name(country, names, provinces):
    """(region, why) for a PGI without an outline: a keyword of its name, a province or region it's named after,
    else the country."""
    for n in names:
        if n in PLACES:
            return PLACES[n], "where it is"
    keys = {k for n in names for k in forms(n)}
    for word, region in KEYWORDS.get(country, []):
        if any(word in k for k in keys):
            return region, f"its name ({word})"
    for k in keys:
        if (country, k) in provinces:
            return provinces[(country, k)], "named after its province or region"
    return country, f"stays in {country}: no outline"


def name_key(name):
    from shape_links import name_key as key
    return key(name)


def forms(name):
    """The names something goes by: each of "X ou Y" and "X / Y", with and without "Grand Cru", without a
    "(IGP - Vin tranquille)" note."""
    name = re.sub(r"\s*\([^)]*\)\s*$", "", str(name or "")).strip()  # a bracketed note: "(multi-regional)"
    out = set()
    for part in {name, *re.split(r" / | ou ", name)}:
        k = name_key(part)
        if k:
            out |= {k, re.sub(r" grand cru$", "", k)}
    return out


def split_name(name, parent=None):
    """(name, aliases) for a register name: the first of "X ou Y" forms, the others aliases ("Coteaux du Layon
    Rablay-sur-Layon ou Rablay": also "Coteaux du Layon Rablay"); a "(IGP - ...)" note dropped."""
    name = re.sub(r"\s*\((?:IGP|AOC|vin)[^)]*\)\s*$", "", str(name), flags=re.I).strip()
    parts = [p.strip() for p in re.split(r" / | ou ", name) if p.strip()]
    aliases = []
    for p in parts[1:]:
        if parent and parts[0].startswith(parent) and not p.startswith(parent):
            p = f"{parent} {p}"
        aliases.append(p)
    return parts[0], aliases


def existing(session):
    """{country: {name forms}}, {inao_id}, {boundary} of the appellations there."""
    from winelib_utils.models import Appellation
    keys, inao, linked = collections.defaultdict(set), set(), set()
    for a in session.query(Appellation):
        country = a.region_obj.country if a.region_obj else None
        for n in [a.name, *(a.aliases or "").split(",")]:
            keys[country] |= forms(n)
        if a.inao_id and (a.type or "") not in ("Denomination", "Mention"):
            inao.add(a.inao_id)
        if a.boundary:
            linked.add(a.boundary)
    return keys, inao, linked


def plan(session):
    """{"new": [row dicts], "renamed": [(appellation, new name)], "skipped": [(source, name, why)]}"""
    import pandas as pd
    from winelib_utils.models import Appellation, Region
    keys, inao_ids, linked = existing(session)
    shapes = outlines()
    regions = {r.name: r for r in session.query(Region)}
    by_country = collections.defaultdict(dict)
    for r in regions.values():
        if r.name != r.country and r.name in shapes:
            by_country[r.country][r.name] = shapes[r.name][0]
    parents = {}
    for a in session.query(Appellation):
        if a.region_obj and a.region_obj.country == "France":
            for k in forms(a.name):
                parents.setdefault(k, a)
    new, skipped = [], []

    def known(country, name, boundary, inao_id=None):
        if boundary and boundary in linked:
            return "its outline is linked already"
        if forms(name) & keys[country]:
            return "there under a form of its name"
        if inao_id and inao_id in inao_ids:
            return "there by its INAO id"
        return None

    taken = {a.name.casefold() for a in session.query(Appellation)}

    def add(row, why=None):
        # names are unique in the database: one already used (in another country) gets its country
        if row["name"].casefold() in taken:
            row = {**row, "aliases": [row["name"], *row["aliases"]], "name": f"{row['name']} ({row['country']})"}
            why = f"{why}; named with its country (the name is taken)"
        taken.add(row["name"].casefold())
        new.append({**row, "why": why})
        keys[row["country"]] |= forms(row["name"]) | {k for a in row["aliases"] for k in forms(a)}
        if row["boundary"]:
            linked.add(row["boundary"])

    def by_outline(country, boundary):
        target, why = place(store_shape(boundary), by_country[country])
        return (target, f"outline {why}") if target else (country, f"stays in {country}: {why}")

    # France: the parcel delimitation's names (premier cru climats left out: they're vineyards)
    d = pd.read_parquet(os.path.join(GEO, "inao_denoms", "denominations.parquet"),
                        columns=["id_denom", "denom", "app", "type_denom"])
    for r in d.itertuples():
        if "premier cru" in r.denom.lower():
            continue
        boundary = f"inao_denom:{r.id_denom}"
        complementary = r.type_denom != "appellation"
        why = known("France", r.denom, boundary, None if complementary else int(r.id_denom))
        if why:
            skipped.append(("INAO", r.denom, why))
            continue
        name, aliases = split_name(r.denom, r.app if complementary else None)
        parent = next((parents[k] for k in forms(r.app) if k in parents), None) if complementary else None
        if parent and parent.region_obj:
            region, how = parent.region_obj.name, f"its appellation's ({parent.name})"
        else:
            region, how = by_outline("France", boundary)
            # outside the regions' outlines (Vendée): where its appellation is
            up = next((parents[k] for k in forms(r.app) if k in parents), None) if r.app != r.denom else None
            if region == "France" and up and up.region_obj:
                region, how = up.region_obj.name, f"its appellation's ({up.name})"
        add({"name": name, "aliases": aliases, "country": "France", "region": region, "boundary": boundary,
             "type": "Denomination" if complementary else "AOP", "subregion": r.app if complementary else None,
             "inao_id": None if complementary else int(r.id_denom), "source": "INAO"}, how)

    # France: the geographic areas' wine AOCs and IGPs
    a = pd.read_parquet(os.path.join(GEO, "inao_aires", "areas.parquet"),
                        columns=["id_denom", "denom", "app", "signe", "categorie"])
    for r in a.itertuples():
        if r.signe not in SIGNS or not WINE.search(str(r.categorie or "")):
            continue
        boundary = f"inao_aires:{r.id_denom}"
        why = known("France", r.denom, boundary, int(r.id_denom) if r.signe != "IGP" else None)
        if why:
            skipped.append(("INAO", r.denom, why))
            continue
        name, aliases = split_name(r.denom)
        region, how = by_outline("France", boundary)
        add({"name": name, "aliases": aliases, "country": "France", "region": region, "boundary": boundary,
             "type": SIGNS[r.signe], "subregion": None, "inao_id": int(r.id_denom) if r.signe != "IGP" else None,
             "source": "INAO"}, how)

    # United States: the AVAs in force (UC Davis keeps each former boundary as its own row, valid_end set: their
    # names, when they differ, are aliases of the current one: "Santa Rita Hills" of Sta. Rita Hills)
    import pyarrow.parquet as pq
    t = pq.read_table(os.path.join(GEO, "shapes", "ava.parquet"), columns=["source_id", "name"]).to_pydict()
    avas = pd.read_parquet(os.path.join(GEO, "us_avas_combined.parquet"), columns=["ava_id", "name", "valid_end"])
    retired = set(avas[avas.valid_end.notna()].ava_id)
    current = dict(zip(avas[avas.valid_end.isna()].ava_id, avas[avas.valid_end.isna()].name))
    old_names = collections.defaultdict(set)
    for aid, old in zip(avas[avas.valid_end.notna()].ava_id, avas[avas.valid_end.notna()].name):
        now = re.sub(r"_\d{8}$", "", aid)
        if now in current and name_key(old) != name_key(current[now]):
            old_names[now].add(old)
    by_boundary = {a.boundary: a for a in session.query(Appellation) if a.boundary}
    aliased = []
    for sid, ava in zip(t["source_id"], t["name"]):
        if sid in retired:
            continue
        boundary = f"ava:{sid}"
        olds = sorted(old_names.get(sid, ()))
        why = known("United States", ava, boundary)
        if why:
            skipped.append(("AVA", ava, why))
            row = by_boundary.get(boundary)
            have = {name_key(x) for x in [row.name, *(row.aliases or "").split(",")]} if row else set()
            missing = [o for o in olds if name_key(o) not in have]
            if row and missing:
                aliased.append((row, missing))
            continue
        region, how = by_outline("United States", boundary)
        add({"name": ava, "aliases": olds, "country": "United States", "region": region, "boundary": boundary,
             "type": "AVA", "subregion": None, "inao_id": None, "source": "AVA"}, how)

    # The EU register (eAmbrosia): every registered wine PDO and PGI
    eu_store = set(pq.read_table(os.path.join(GEO, "shapes", "eu.parquet"), columns=["source_id"]).column(0).to_pylist())
    aires_names = {}
    t = pq.read_table(os.path.join(GEO, "shapes", "inao_aires.parquet"), columns=["source_id", "name"]).to_pydict()
    for sid, n in zip(t["source_id"], t["name"]):
        for k in forms(n):
            aires_names.setdefault(k, f"inao_aires:{sid}")
    pdo_ids = {a.pdo_id for a in session.query(Appellation) if a.pdo_id}
    provinces = province_regions()
    for g in eu_register():
        country = EU_COUNTRIES.get(g["countries"], g["countries"])
        boundary = f"eu:{g['fileName']}" if g["fileName"] in eu_store else None
        names = [x.strip() for x in g["protectedName"].split(" / ") if x.strip()]
        latin = [latin_name(x) for x in names]
        latin = sorted(latin, key=lambda x: not LATIN.fullmatch(x))  # a Latin-script form leads (Chinese: the pinyin)
        name, aliases = latin[0], list(dict.fromkeys([*latin[1:], *(x for x in names if x not in latin)]))
        if name in SAME:
            aliases, name = [name, *aliases], SAME[name]
        if g["fileName"] in pdo_ids:
            skipped.append(("EU", name, "there by its EU id"))
            continue
        # a French IGP whose INAO outline is linked already, under an older name (Vin de Pays du Vaucluse)
        if country == "France" and any(aires_names.get(k) in linked for x in names for k in forms(x)):
            skipped.append(("EU", name, "there by its INAO outline"))
            continue
        why = known(country, name, boundary) or next((known(country, a, None) for a in aliases if known(country, a, None)), None)
        if why:
            skipped.append(("EU", name, why))
            continue
        pgi = g["geographicalIndicatorTypeCode"] == "PGI"
        if boundary:
            region, how = by_outline(country, boundary)
        elif name in PLACES:
            region, how = PLACES[name], "where it is"
        else:
            region, how = by_name(country, [name, *aliases], provinces)
        add({"name": name, "aliases": aliases, "country": country, "region": region, "boundary": boundary,
             "type": (PGI_TYPES if pgi else PDO_TYPES).get(country, "PGI" if pgi else "PDO"), "subregion": None,
             "inao_id": None, "source": "EU", "pdo_id": g["fileName"], "category": "Wine",
             "registration_date": g.get("registrationDate"),
             "location_link": f"{EAMBROSIA_PAGE}{g['appUniqueId']}"}, how)

    # Other countries' official lists
    typed = []
    import csv
    import glob
    rows_by_key = collections.defaultdict(list)
    for a in session.query(Appellation):
        if a.region_obj:
            for n in [a.name, *(a.aliases or "").split(",")]:
                for k in forms(n):
                    rows_by_key[(a.region_obj.country, k)].append(a)
    for path in sorted(glob.glob(os.path.join(REGISTERS, "*.csv"))):
        country = REGISTER_COUNTRIES.get(os.path.splitext(os.path.basename(path))[0])
        if not country:
            continue
        with open(path, encoding="utf-8-sig", newline="") as f:
            rows = [r for r in csv.DictReader(f) if (r.get("name") or "").strip()]
        within = {r["name"].strip(): (r.get("within") or "").strip() for r in rows}
        here = {name for name, r in regions.items() if r.country == country}
        for r in rows:
            name = r["name"].strip()
            aliases = [x.strip() for x in (r.get("aliases") or "").split("|") if x.strip()]
            kind = (r.get("type") or "").strip() or None
            hits = {a.id: a for k in forms(name) | {k for x in aliases for k in forms(x)}
                    for a in rows_by_key.get((country, k), [])}
            if hits or known(country, name, None):
                skipped.append((f"register {country}", name, "there already"))
                for a in hits.values():
                    if kind and not (a.type or "").strip():
                        typed.append((a, kind))
                continue
            # the region: the row's own, one it's within, or the country
            region, how, up, seen = None, None, name, set()
            explicit = (r.get("region") or "").strip()
            if explicit in here:
                region, how = explicit, "the list's region"
            while not region and up and up not in seen:
                seen.add(up)
                if up in here and up != country:
                    region, how = up, f"within {up}"
                up = within.get(up)
            if not region:
                region, how = country, f"stays in {country}"
            add({"name": name, "aliases": aliases, "country": country, "region": region, "boundary": None,
                 "type": kind, "subregion": within.get(name) or None, "inao_id": None,
                 "details": (r.get("note") or "").strip() or None,
                 "source": f"register ({os.path.basename(path)})"}, how)

    # The national appellations
    renamed = []
    for old, new_name in RENAMES.items():
        row = session.query(Appellation).filter(Appellation.name == old).one_or_none()
        if row and not session.query(Appellation).filter(Appellation.name == new_name).count():
            renamed.append((row, new_name))
            keys[row.region_obj.country if row.region_obj else None] |= forms(new_name)
    for name, country in NATIONAL.items():
        if forms(name) & keys[country]:
            skipped.append(("national", name, "there already"))
            continue
        add({"name": name, "aliases": [], "country": country, "region": country, "boundary": None, "type": "National",
             "subregion": None, "inao_id": None, "source": "national"}, "the country")
    return {"new": new, "renamed": renamed, "aliased": aliased, "typed": typed, "skipped": skipped}


def report(p):
    out = ["Missing appellations (docs/reference-data.md)", ""]
    out += [f"Renamed: {len(p['renamed'])}"] + [f"  {a.name} -> {n}" for a, n in p["renamed"]]
    out += ["", f"Former names added as aliases: {len(p['aliased'])}"]
    out += [f"  {a.name}: {', '.join(names)}" for a, names in p["aliased"]]
    out += ["", f"Types filled from the official lists: {len(p['typed'])}"]
    out += [f"  {a.name}: {kind}" for a, kind in p["typed"]]
    out += ["", f"New appellations: {len(p['new'])}"]
    groups = collections.defaultdict(list)
    for r in p["new"]:
        groups[(r["country"], r["source"], r["type"])].append(r)
    for (country, source, kind), rows in sorted(groups.items()):
        out.append(f"  {country}, {source} {kind} ({len(rows)})")
        by_region = collections.defaultdict(list)
        for r in rows:
            by_region[r["region"]].append(r)
        for region, rs in sorted(by_region.items()):
            out.append(f"    -> {region} ({len(rs)}): " + "; ".join(
                r["name"] + (f" (also {', '.join(r['aliases'])})" if r["aliases"] else "") + f" [{r['why']}]" for r in rs))
    out += ["", f"Already there: {len(p['skipped'])}"]
    for (source, why), rows in sorted(collections.Counter((s, w) for s, _, w in p["skipped"]).items()):
        out.append(f"  {source}, {why}: {rows}")
    return out


def apply(session, p):
    from winelib_utils.models import Appellation, Region
    for row, new_name in p["renamed"]:
        aliases = [x.strip() for x in (row.aliases or "").split(",") if x.strip()]
        row.aliases = ", ".join(dict.fromkeys(aliases + [row.name]))
        row.name = new_name
    for row, kind in p["typed"]:
        row.type = kind
    for row, names in p["aliased"]:
        aliases = [x.strip() for x in (row.aliases or "").split(",") if x.strip()]
        row.aliases = ", ".join(dict.fromkeys(aliases + names))
    ids = {r.name: r.id for r in session.query(Region)}
    for r in p["new"]:
        if r["region"] not in ids:  # a country without any region yet (Brazil): its country-level one
            region = Region(name=r["region"], country=r["country"])
            session.add(region)
            session.flush()
            ids[region.name] = region.id
        date = None
        if r.get("registration_date"):
            from datetime import datetime
            date = datetime.strptime(r["registration_date"], "%d/%m/%Y").date()
        session.add(Appellation(name=r["name"], aliases=", ".join(r["aliases"]) or None, region_id=ids[r["region"]],
                                boundary=r["boundary"], type=r["type"], subregion=r["subregion"], inao_id=r["inao_id"],
                                pdo_id=r.get("pdo_id"), category=r.get("category"), registration_date=date,
                                details=r.get("details"),
                                location_link=r.get("location_link")))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--commit", action="store_true", help="write (take a backup first); without it, a dry run")
    args = parser.parse_args()
    import config
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    session = sessionmaker(bind=create_engine(config.DB_URL))()
    try:
        p = plan(session)
        lines = report(p)
        os.makedirs(os.path.dirname(REPORT), exist_ok=True)
        with open(REPORT, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        counts = collections.Counter(r["country"] for r in p["new"])
        print(f"{len(p['new'])} new appellations ({', '.join(f'{c} {n}' for c, n in counts.most_common())}); "
              f"{len(p['renamed'])} renamed; {len(p['skipped'])} already there. Report: {os.path.relpath(REPORT, ROOT)}")
        if args.commit:
            apply(session, p)
            session.commit()
            print("Saved.")
        else:
            print("Dry run: nothing saved (--commit to save).")
    finally:
        session.close()


if __name__ == "__main__":
    main()
