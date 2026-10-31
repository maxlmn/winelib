"""Grand cru and premier cru, for the maps' darker shades: 2 for a grand cru, 1 for a premier cru, 0 otherwise.

No source says so outright, so:
- an appellation by its name: "... Grand Cru ...", one of Burgundy's 33 grand cru appellations (Chambertin, Musigny,
  Corton...), or "... Premier Cru" / "1er Cru". Saint-Émilion Grand Cru is a whole appellation's tier, not a cru: none;
- a vineyard by where it lies: mostly (CONTAINED) inside an INAO grand cru's vines (inao_denom outlines named as
  above: Burgundy's and Alsace's grand crus), else inside a premier cru's; INAO's own premier cru climats
  ("vineyard:inao-pc:...") are premier crus at least. INAO's premier cru outlines include the grand cru land
  (it may be declassified), so grand cru is tried first. Champagne's crus are whole villages (the échelle des crus):
  the store's champagne_cru source says each one's level ("grand cru", "premier cru").
Worked out once per store (lru_cache), from the store's display outlines.
"""
import re
import unicodedata
from functools import lru_cache

CONTAINED = 0.5
# "grand cru", "premier cru", "1er cru" as INAO writes them in its names: capitalised for showing
CRU_WORDS = re.compile(r"\b([Gg]rand|[Pp]remier|1er) cru\b")


def cru_case(name):
    """A name with its rank capitalised: "Alsace grand cru Brand" -> "Alsace Grand Cru Brand", "Pommard premier cru
    Les Epenots" -> "Pommard Premier Cru Les Epenots" (the official names write it in lower case)"""
    return CRU_WORDS.sub(lambda m: f"{m.group(1).capitalize()} Cru", name) if name else name


NOT_CRUS = ("saint-emilion grand cru", "saint emilion grand cru", "st-emilion grand cru", "st emilion grand cru")

BURGUNDY_GRAND_CRUS = {
    "chambertin", "chambertin-clos de beze", "chapelle-chambertin", "charmes-chambertin", "griotte-chambertin",
    "latricieres-chambertin", "mazis-chambertin", "mazoyeres-chambertin", "ruchottes-chambertin",
    "clos de la roche", "clos saint-denis", "clos de tart", "clos des lambrays", "bonnes-mares", "musigny",
    "clos de vougeot", "clos vougeot", "clos de vougeot ou clos vougeot", "echezeaux", "grands-echezeaux",
    "la grande rue", "la romanee", "la tache", "richebourg", "romanee-conti", "romanee-saint-vivant",
    "corton", "corton-charlemagne", "charlemagne", "montrachet", "le montrachet", "chevalier-montrachet",
    "batard-montrachet", "bienvenues-batard-montrachet", "criots-batard-montrachet",
}


def _fold(name):
    text = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", text.replace("\u2019", "'")).strip()


def name_level(name):
    """2, 1 or 0 from a name alone."""
    n = _fold(name)
    if n.startswith(NOT_CRUS):
        return 0
    if "grand cru" in n or n in BURGUNDY_GRAND_CRUS:
        return 2
    if "premier cru" in n or re.search(r"\b1er cru\b", n):
        return 1
    return 0


def appellation_level(a):
    return name_level(a.name)


@lru_cache
def _vineyard_levels():
    """{vineyard store source_id: 1 or 2}"""
    import numpy as np
    import pyarrow.parquet as pq
    import shapely
    import geo

    def read(source, columns):
        path = f"{geo.SHAPES_DIR}/{source}.parquet"
        try:
            return pq.read_table(path, columns=columns).to_pydict()
        except (OSError, ValueError):
            return None

    inao, vines = read("inao_denom", ["name", "display"]), read("vineyard", ["source_id", "display"])
    if not vines:
        return {}
    levels = {}
    shapes = shapely.make_valid(shapely.from_wkb(np.array(vines["display"], dtype=object)))  # rounded: may self-touch
    areas = shapely.area(shapes)
    for level in (1, 2):  # grand cru last: it wins
        crus = [g for n, g in zip(inao["name"], inao["display"]) if g is not None and name_level(n) == level] if inao else []
        if not crus:
            continue
        area = shapely.union_all(shapely.make_valid(shapely.from_wkb(np.array(crus, dtype=object))))
        shapely.prepare(area)
        near = np.flatnonzero(shapely.intersects(shapes, area))
        inside = shapely.area(shapely.intersection(shapes[near], area))
        for i, a in zip(near, inside):
            if areas[i] and a / areas[i] >= CONTAINED:
                levels[vines["source_id"][i]] = level
    for sid in vines["source_id"]:  # INAO's premier cru climats are premier crus, whatever they straddle
        if sid.startswith("inao-pc:"):
            levels[sid] = 1
    return levels


@lru_cache
def _champagne_levels():
    """{champagne_cru source_id: 1 or 2}: the store's own levels"""
    import pyarrow.parquet as pq
    import geo
    try:
        t = pq.read_table(f"{geo.SHAPES_DIR}/champagne_cru.parquet", columns=["source_id", "level"]).to_pydict()
    except (OSError, ValueError):
        return {}
    return {sid: name_level(level or "") for sid, level in zip(t["source_id"], t["level"])}


def vineyard_level(v):
    boundary = getattr(v, "boundary", None) or ""
    if boundary.startswith("champagne_cru:"):
        return _champagne_levels().get(boundary.split(":", 1)[1], 0)
    if not boundary.startswith("vineyard:"):
        return 0
    return _vineyard_levels().get(boundary.split(":", 1)[1], 0)


def warm():
    """Works out the vineyards' crus ahead of the first map request (geo.warm)."""
    _vineyard_levels()


def reset():
    _vineyard_levels.cache_clear()
    _champagne_levels.cache_clear()
