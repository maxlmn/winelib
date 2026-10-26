"""Shape links: each appellation and vineyard linked to its outline in the shape store (data/geo/shapes/): fills
the `boundary` column ("inao:291", "eu:PDO-IT-A0281", "vineyard:inao-pc:257") following the link rules in
data/shape_sources.json, only where the store has that shape (docs/plans/shape-storage.md). It doesn't create rows
nor touch wines: the map draws a row's boundary, and a row without one isn't drawn.

Settings › Maintenance › Shape links runs it (after downloading or building the store, or adding appellations and
vineyards); geo_scripts/link_shapes.py on a PC. The name rules shared with the PC's scripts (norm, key, ALIASES:
Australia's GIs, linked by name) are here, and geo_scripts/build_shapes.py takes them from here.
"""
import json
import os
import re
import unicodedata

from sqlalchemy import inspect, text

SOURCES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "shape_sources.json")
# Appellation names that aren't the official ones -> the official name, per country (Australia's GIs)
ALIASES = {
    "Australia": {
        "mclaren valley": "mclaren vale",
        "south western australia": "south west australia",
    },
}


def norm(name):
    ascii_ = unicodedata.normalize("NFKD", str(name or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", ascii_.lower()).strip()


def key(country, name):
    """The normalised official name an appellation of this country is looked up by."""
    k = norm(name)
    return ALIASES.get(country, {}).get(k, k)


def slug(name):
    return norm(name).replace(" ", "-")


LOCAL_FILE = "sources.local.json"


def load_sources(path=SOURCES_FILE, geo_dir=None):
    """{name: source}: the sources of the shape store and their link rules; with geo_dir, its sources.local.json's
    too (an installation's own: a source of the same name replaces the shipped one, in its place; others are added)."""
    with open(path, encoding="utf-8") as f:
        sources = {spec["name"]: spec for spec in json.load(f)["sources"]}
    local = os.path.join(geo_dir, LOCAL_FILE) if geo_dir else None
    if local and os.path.exists(local):
        with open(local, encoding="utf-8") as f:
            sources.update({spec["name"]: spec for spec in json.load(f)["sources"]})
    return sources


TABLES = ("appellations", "vineyards")
EXAMPLES = 8


def store_ids(geo_dir, sources):
    """{source: {source_id: shape name}} for the sources whose store file exists."""
    import pyarrow.parquet as pq
    out = {}
    for name in sources:
        path = os.path.join(geo_dir, "shapes", f"{name}.parquet")
        if os.path.exists(path):
            table = pq.read_table(path, columns=["source_id", "name"])
            out[name] = dict(zip(table.column(0).to_pylist(), table.column(1).to_pylist()))
    return out


def name_key(name):
    from unidecode import unidecode
    return re.sub(r"[^a-z0-9]+", " ", unidecode(str(name or "")).lower()).strip()


def store_names(geo_dir, source, country=None):
    """{(country code, name): {source_id}} for a source whose ids carry the country (PDO-IT-A1234), or with
    `country`, a one-country source (INAO's areas: France): each of the names a shape goes by ("Bellet / Vin de
    Bellet" and "Coteaux du Layon Faye d'Anjou ou Faye" are both)."""
    import pyarrow.parquet as pq
    out = {}
    path = os.path.join(geo_dir, "shapes", f"{source}.parquet")
    if not os.path.exists(path):
        return out
    for sid, name in zip(*pq.read_table(path, columns=["source_id", "name"]).to_pydict().values()):
        parts = str(sid).split("-")
        code = country or (parts[1] if len(parts) >= 2 else None)
        if not code or not name:
            continue
        # each name, and the whole ("Collio Goriziano / Collio" is also "Collio Goriziano (Collio)")
        for alt in {*re.split(r" / | ou ", str(name)), str(name)}:
            out.setdefault((code, name_key(alt)), set()).add(sid)
    return out


def rules_of(spec):
    """A source's link rules: "link" is one rule or a list of them."""
    link = spec.get("link")
    return [] if not link else link if isinstance(link, list) else [link]


def comparable(name):
    """A name for comparing: accents off, lowercase, any punctuation (en dash, curly apostrophe...) a space, in any
    script (norm keeps ASCII only: a Greek or Bulgarian name would come out empty)."""
    import unicodedata
    text = "".join(c for c in unicodedata.normalize("NFKD", str(name or "")) if not unicodedata.combining(c))
    return re.sub(r"[\W_]+", " ", text.casefold()).strip()


def names_match(a, b):
    """Whether a row's name and a shape's name are the same place, loosely: equal once normalised, or one inside
    the other (Amoureuses / Les Amoureuses)."""
    a, b = comparable(a), comparable(b)
    if not a or not b:
        return False
    short, long_ = sorted((a, b), key=len)
    return a == b or (len(short) >= 4 and f" {short} " in f" {long_} ")


def region_keys(region, link):
    """A region's keys as in the vineyard file names (the vineyard source's files, vineyard:<region>:<id>): Bourgogne -> bourgogne; an alias
    can name several (Burgundy -> bourgogne and inao-pc, the INAO premier crus: Burgundy's, and Chaume in the Loire)."""
    k = str(region or "").lower().replace(" ", "_").replace("/", "_")
    keys = (link.get("region_aliases") or {}).get(k, k)
    return [keys] if isinstance(keys, str) else list(keys)


def candidates(row, link, names=None):
    """The source_ids a row could have under one link rule ([] when the rule doesn't apply to it)."""
    by = link["by"]
    if by == "country_name":
        # The shape's id is "<country>:<appellation name>" (build_admin_areas.py writes them so)
        return [f"{row['country']}:{row['name']}"] if row["country"] and row["name"] else []
    if by == "store_name":
        # By the shape's own name within the row's country, only for rows without the id (when_empty): an alias
        # first (a spelling or a renamed denomination), else one shape of exactly that name
        if row.get(link.get("when_empty")) not in (None, "") or not row["name"]:
            return []
        code = (link.get("country_codes") or {}).get(row["country"])
        if link.get("country"):  # a one-country source
            code = link["country"] if row["country"] == link["country"] else None
        if not code:
            return []
        alias = (link.get("aliases") or {}).get(f"{row['country']} / {row['name']}")
        if alias:
            return [alias]
        found = (names or {}).get((code, name_key(row["name"])), ())
        return list(found) if len(found) == 1 else []
    if by == "name":
        if row["country"] != link.get("country") or not row["name"]:
            return []
        return [slug(key(link["country"], row["name"]))]
    value = row.get(by)
    if value is None or str(value).strip() == "":
        return []
    value = str(value).strip()
    prefix = link.get("strip_prefix")
    if prefix:
        if not value.startswith(prefix):
            return []
        value = value[len(prefix):]
    if link.get("region"):
        if not row["region"]:
            return []
        return [f"{k}:{value}" for k in region_keys(row["region"], link)]
    return [value]


def rows(conn, table, columns, has_boundary=True):
    """The table's rows with their region's name and country; only the columns the link rules use."""
    cols = ", ".join(f"t.{c}" for c in sorted(columns))
    current = "t.boundary" if has_boundary else "NULL AS boundary"  # a dry run before the column exists
    sql = (f"SELECT t.id, t.name, {current}, r.name AS region, r.country{', ' + cols if cols else ''} "
           f"FROM {table} t LEFT JOIN regions r ON r.id = t.region_id ORDER BY t.id")
    return [dict(r._mapping) for r in conn.execute(text(sql))]


def ensure_column(engine, table, commit):
    if "boundary" in {c["name"] for c in inspect(engine).get_columns(table)}:
        return False
    if commit:
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN boundary VARCHAR"))
    return True


def plan(table_rows, rules, store, names=None):
    """{row id: new boundary or None}, plus the report: linked per source; the rows a rule applied to but the
    store has no shape for ([(row, ["source:id"])]); the rows whose id is in several files (Burgundy: Weinlagen
    and the INAO premier crus share ids) with no single shape of their name: not linked; and the linked rows whose
    shape has another name ([(row, link, shape name)]), to check."""
    new, linked, missing, ambiguous, mismatched = {}, {}, [], [], []
    for row in table_rows:
        found, tried = None, []
        for source, link in rules:
            ids = store.get(source, {})
            cands = candidates(row, link, (names or {}).get(source))
            present = [sid for sid in cands if sid in ids]
            if len(present) > 1:  # the same id in several files: the one with the row's name
                named = [sid for sid in present if names_match(row["name"], ids[sid])]
                if len(named) != 1:
                    ambiguous.append((row, [f"{source}:{sid} ({ids[sid]})" for sid in present]))
                    tried = None
                    break
                present = named
            if present:
                found = f"{source}:{present[0]}"
                if ids[present[0]] and not names_match(row["name"], ids[present[0]]):
                    mismatched.append((row, found, ids[present[0]]))
                break
            if link["by"] != "country_name":  # an area by name: only when the store has it, never "missing"
                tried += [f"{source}:{sid}" for sid in cands]
        new[row["id"]] = found
        if found:
            linked[found.split(":", 1)[0]] = linked.get(found.split(":", 1)[0], 0) + 1
        elif tried:
            missing.append((row, tried))
    return new, linked, missing, ambiguous, mismatched


def in_store(boundary, store):
    """Whether a boundary link's shape is in the store ({source: {source_id: name}})."""
    source, _, sid = boundary.partition(":")
    return sid in store.get(source, {})


def link(engine, geo_dir, commit=False, sources_file=SOURCES_FILE):
    """Works out (and with commit saves) every row's boundary. {"store": {source: shapes}, "absent": [sources not
    built], "tables": {table: {"rows", "added", "linked": {source: n}, "missing", "ambiguous", "mismatched",
    "none", "changes": [(row, old boundary, new boundary)]}}}. Settings › Maintenance › Shape links, and geo_scripts/link_shapes.py on a PC.
    ValueError without a store."""
    sources = load_sources(sources_file, geo_dir)
    store = store_ids(geo_dir, sources)
    if not store:
        raise ValueError(f"No shape store in {os.path.join(geo_dir, 'shapes')}: download the map outlines, or build them (geo_scripts/build_shapes.py)")
    out = {"store": {s: len(ids) for s, ids in store.items()}, "absent": [s for s in sources if s not in store],
           "tables": {}}
    for table in TABLES:
        rules = [(name, link) for name, spec in sources.items() for link in rules_of(spec)
                 if link.get("table") == table]
        if not rules:
            continue
        added = ensure_column(engine, table, commit)
        columns = {link["by"] for _, link in rules if link["by"] not in ("name", "store_name", "country_name")}
        columns |= {link["when_empty"] for _, link in rules if link.get("when_empty")}
        names = {source: store_names(geo_dir, source, link.get("country")) for source, link in rules
                 if link["by"] == "store_name"}
        with engine.connect() as conn:
            table_rows = rows(conn, table, columns, has_boundary=commit or not added)
        new, linked, missing, ambiguous, mismatched = plan(table_rows, rules, store, names)
        # A current link is kept when no rule finds another and its shape is still in the store (a rule that went
        # elsewhere, sources.local.json missing on this machine), or when it names a source not listed (set by hand)
        changes = [(r, r["boundary"], new[r["id"]]) for r in table_rows if r["boundary"] != new[r["id"]]
                   and (r["boundary"] is None or (r["boundary"].split(":", 1)[0] in sources
                                                  and (new[r["id"]] is not None or not in_store(r["boundary"], store))))]
        out["tables"][table] = {
            "rows": len(table_rows), "added": added, "linked": linked, "missing": missing, "ambiguous": ambiguous,
            "mismatched": mismatched, "none": len(table_rows) - sum(linked.values()) - len(missing) - len(ambiguous),
            "changes": changes}
        if commit and changes:
            with engine.begin() as conn:
                conn.execute(text(f"UPDATE {table} SET boundary = :b WHERE id = :id"),
                             [{"b": b, "id": r["id"]} for r, _, b in changes])
    return out
