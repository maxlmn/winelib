"""
The Liv-ex LWIN list for the app: the wine form's LWIN suggestions and Settings › Maintenance › LWIN codes, which
matches cellar wines without one (fill_missing_lwin; a run gives each LWIN it saves to the cuvée's other vintages).

The list, prepared once on a computer:
    python app/api/tasks/match_lwin.py --preprocess    # data/LWINdatabase.xlsx -> data/lwin_lookup.json
    python app/api/tasks/match_lwin.py --build-index   # -> data/lwin/lwin.sqlite, the file the app reads (copy it
                                                       #    to the server's data/lwin/)
"""
import os
import sys
import argparse
import json
import logging
import re
from collections import defaultdict

from unidecode import unidecode

# app/api on the path (models, paths, tasks), for running this file as a script
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import Bottle, Wine

# --- Constants ---
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
LWIN_XLSX = os.path.join(DATA_DIR, "LWINdatabase.xlsx")
LWIN_JSON = os.path.join(DATA_DIR, "lwin_lookup.json")
# The same entries in an indexed SQLite file: the app looks one producer up without loading 90 MB of JSON
LWIN_DB = os.getenv("LWIN_DB", os.path.join(DATA_DIR, "lwin", "lwin.sqlite"))
ENTRY_FIELDS = ("lwin", "display_name", "display_name_norm", "producer_name", "wine", "wine_norm_light", "wine_norm",
                "colour")

# Column indices (0-based) from the LWIN xlsx
COL_LWIN = 0
COL_STATUS = 1
COL_DISPLAY_NAME = 2
COL_PRODUCER_NAME = 4
COL_WINE = 5
COL_COLOUR = 11


# --- Normalization helpers ---

def normalize_light(text):
    """Light normalization: unidecode, lowercase, hyphens to spaces, strip punctuation."""
    if not text or str(text).strip() in ("", "NA"):
        return ""
    text = unidecode(str(text)).lower().strip()
    text = text.replace("-", " ")
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

manual_list = {
    "marcel lapierre": "m et c lapierre",
    "la porte saint jean" : "sylvain dittiere",
    "clape" : "auguste clape",
    "dureuil janthial": "vincent dureuil janthial",
    "roses de jeanne": "cedric bouchard",
    "beau paysage": "beau paysage tsugane",
    "laisse tomber": "laisse tomber bastian wolber",
    "de la pepiere": "la pepiere",
    "soldera": "soldera case basse",
    "stella di campalto": "stella di campalto podere sgiuseppe",
    "occidental": "occidental kistler",
    "lopez de heredia": "r lopez de heredia",
    "gb burlotto":"comm gb burlotto",
    "taganan parcela margalagua":"parcela margalagua taganan",
    "taganan margalagua":"parcela margalagua taganan",
    "lousas vinas de aldea":"lousas vina aldea",
    "vina tondonia reserva":"tondonia tinto reserva",
    "pichon lalande": "pichon longueville comtesse de lalande",
    "des vignes mayne":"julien guillot vignes du maynes",
    "de beaucastel":"famille perrin",
    "vouette sorbee":"vouette et sorbee",
    "ile de vergelesses":"ile des vergelesses",
    "la santa du ursula": "la santa de ursula",
    "premier grand cru classe a":"",
    "cru bourgeois":"",
    "les faraunieres": "faraunieres blanc",
    "les mines": "mines rouge",
    "cinquieme grand cru classe": "5eme cru classe",
    #"vin de pays du languedoc": "pays herault rouge",
    "village":"",
    "de la cras": "marc soyard",
    "auxey duresses": "auxey duresses blanc",
    "troisieme grand cru classe":"3eme cru classe",
    #"sauternes 7":"no 6",
    "jean louis chave":"domaine jean louis chave",
    #"hermitage":"hermitage rouge",
    "les orizeaux":"orizeaux extra brut",
    "second grand cru classe":"2eme cru classe",
}
def normalize(text):
    """Aggressive normalization: light + prefix removal + word replacements."""
    text = normalize_light(text)
    if not text:
        return ""
    # Remove common prefixes that differ between databases
    for prefix in ("domaine ", "dom ", "chateau ", "maison ",
                    "cave ", "clos ", "mas ", "bodega ", "bodegas ",
                    "tenuta ", "cantina ", "azienda agricola ", "weingut "):
        if text.startswith(prefix):
            text = text[len(prefix):]
    # Word replacements
    text = text.replace("tinto", "red")
    text = text.replace("vineyards", "")
    text = text.replace("cellars", "")
    text = text.replace("blanco", "white")
    text = text.replace(" et fils", "")
    text = text.replace(" des ", " ")
    #text = text.replace(" du ", " ")
    text = text.replace("48 mois", "")
    text = text.replace("60 mois", "")
    text = text.replace("72 mois", "")
    for k,v in manual_list.items():
        if text == k:
            text = v

    text = re.sub(r"\s+", " ", text).strip()
    return text


# --- Preprocess xlsx → JSON ---

def preprocess_lwin():
    """
    Read the Liv-ex xlsx once and write a fast-loading JSON lookup file.
    Only 'Live' entries are kept, keyed by normalized producer name.
    """
    import openpyxl
    
    print(f"[*] Reading {LWIN_XLSX}...")
    wb = openpyxl.load_workbook(LWIN_XLSX, read_only=True)
    ws = wb.active
    
    lookup = defaultdict(list)
    count = 0
    skipped = 0
    
    for row in ws.iter_rows(min_row=2, values_only=True):
        status = row[COL_STATUS]
        if status != "Live":
            skipped += 1
            continue
        
        lwin_code = row[COL_LWIN]
        if lwin_code is None:
            continue
        
        producer_name = str(row[COL_PRODUCER_NAME] or "")
        wine_name = str(row[COL_WINE] or "")
        display_name = str(row[COL_DISPLAY_NAME] or "")
        colour = str(row[COL_COLOUR] or "")
        
        norm_producer_light = normalize_light(producer_name)
        norm_producer_aggr = normalize(producer_name)
        if not norm_producer_light:
            continue
        
        entry = {
            "lwin": str(int(lwin_code)),
            "display_name": display_name,
            "display_name_norm": normalize_light(display_name),
            "producer_name": producer_name,
            "wine": wine_name,
            "wine_norm_light": normalize_light(wine_name),
            "wine_norm": normalize(wine_name),
            "colour": colour,
        }
        # Index under both light and aggressive producer keys
        lookup[norm_producer_light].append(entry)
        if norm_producer_aggr != norm_producer_light:
            lookup[norm_producer_aggr].append(entry)
        count += 1
    
    wb.close()
    
    print(f"[*] Writing {LWIN_JSON}...")
    with open(LWIN_JSON, "w", encoding="utf-8") as f:
        json.dump(lookup, f, ensure_ascii=False, indent=4)
    
    size_mb = os.path.getsize(LWIN_JSON) / (1024 * 1024)
    print(f"[OK] Preprocessed {count:,} live entries ({skipped:,} skipped) across {len(lookup):,} producers.")
    print(f"     Saved to {LWIN_JSON} ({size_mb:.1f} MB)")


# --- Load preprocessed JSON ---

def _match_against(cuvee_norm, lwin_entries, norm_key):
    """
    Try to find an exact/substring match using the given norm_key field.
    Returns the best matching entry or None.
    """
    if not cuvee_norm:
        return None
    
    best = None
    best_score = 0
    
    for entry in lwin_entries:
        lwin_wine = entry.get(norm_key, "")
        if not lwin_wine:
            continue
        
        # Exact string match
        if cuvee_norm == lwin_wine:
            return entry  # Perfect match
        
        # Substring match in either direction
        if cuvee_norm in lwin_wine or lwin_wine in cuvee_norm:
            score = min(len(cuvee_norm), len(lwin_wine)) / max(len(cuvee_norm), len(lwin_wine))
            if score > best_score:
                best_score = score
                best = entry
    
    return best


def find_exact_match(cuvee, lwin_entries):
    """
    Two-pass matching: first light normalization, then aggressive.
    """
    cuvee_light = normalize_light(cuvee)
    cuvee_aggr = normalize(cuvee)
    
    # Pass A: light normalization
    match = _match_against(cuvee_light, lwin_entries, "wine_norm_light")
    if match:
        return match
    
    # Pass B: aggressive normalization
    return _match_against(cuvee_aggr, lwin_entries, "wine_norm")



def build_index(json_path=LWIN_JSON, db_path=LWIN_DB):
    """lwin_lookup.json → an SQLite table keyed by normalized producer name."""
    import sqlite3
    with open(json_path, encoding="utf-8") as f:
        lookup = json.load(f)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute(f"CREATE TABLE entries (key TEXT, {', '.join(f + ' TEXT' for f in ENTRY_FIELDS)})")
    conn.executemany(f"INSERT INTO entries VALUES (?, {', '.join('?' * len(ENTRY_FIELDS))})",
                     ((key, *(e.get(f, "") for f in ENTRY_FIELDS)) for key, entries in lookup.items() for e in entries))
    conn.execute("CREATE INDEX idx_key ON entries (key)")
    conn.commit()
    n = conn.execute("SELECT count(*) FROM entries").fetchone()[0]
    conn.execute("VACUUM")
    conn.close()
    print(f"[OK] {n:,} entries for {len(lookup):,} producer keys -> {db_path} "
          f"({os.path.getsize(db_path) / 1048576:.1f} MB)")


PRODUCER_PREFIXES = ("domaine", "dom", "chateau", "maison", "cave", "mas", "bodega", "bodegas", "tenuta", "cantina",
                     "azienda", "agricola", "weingut", "du", "de", "des", "d", "la", "le", "les")


def producer_keys(producer_name):
    """Index keys to try for a producer, most exact first: the light and aggressive forms, then with the leading
    "Domaine du", "Château de"... taken off one word at a time ("Domaine du Clos de Tart" -> "clos de tart")."""
    light = normalize_light(producer_name)
    keys = [light, normalize(producer_name)]
    words = light.split()
    while len(words) > 1 and words[0] in PRODUCER_PREFIXES:
        words = words[1:]
        keys += [" ".join(words), normalize(" ".join(words))]
    return [k for k in dict.fromkeys(keys) if k]


def entries_for(producer_name, db_path=LWIN_DB):
    """The LWIN entries of a producer (light key first, then aggressive), from the SQLite index. [] if none."""
    import sqlite3
    if not os.path.exists(db_path):
        raise FileNotFoundError(db_path)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        for key in producer_keys(producer_name):
            rows = conn.execute(f"SELECT {', '.join(ENTRY_FIELDS)} FROM entries WHERE key = ?", (key,)).fetchall()
            if rows:
                return [dict(zip(ENTRY_FIELDS, r)) for r in rows]
        return []
    finally:
        conn.close()


def _mostly_same(cuvee, entry, appellation="", ratio=0.6):
    """The entry's wine name is the cuvée, with or without the appellation ("Cote Rotie, Cote Brune"), or one name
    holds most of the other."""
    for norm, key in ((normalize_light, "wine_norm_light"), (normalize, "wine_norm")):
        theirs = entry.get(key) or ""
        if not theirs:
            continue
        for mine in {norm(cuvee), norm(f"{appellation} {cuvee}"), norm(f"{cuvee} {appellation}")}:
            if mine and (mine == theirs or ((mine in theirs or theirs in mine) and
                                            min(len(mine), len(theirs)) / max(len(mine), len(theirs)) >= ratio)):
                return True
    return False


def suggest(lwin_entries, producer_name, cuvee="", appellation_name="", threshold=80, limit=3):
    """LWIN candidates for one wine among its producer's entries, best first: the same rules as the batch below
    (an exact cuvée match, else fuzzy on producer + appellation + cuvée). [(entry, match type, score)]."""
    cuvee = cuvee or ""
    appellation_name = appellation_name or ""
    if not lwin_entries:
        return []
    if cuvee:
        match = find_exact_match(cuvee, lwin_entries)
        # find_exact_match takes substrings: "Clos de Tart" loses its "clos" to normalize() and "de tart" is in
        # "la forge de tart". Exact only when the names are mostly the same, else the fuzzy pass decides.
        if match and _mostly_same(cuvee, match, appellation_name):
            return [(match, "EXACT", 100)]
    lwin_producer = normalize_light(lwin_entries[0]["producer_name"])
    names = [
        (normalize_light(producer_name) + " " + normalize(appellation_name) + " " + normalize(cuvee)).strip(),
        (lwin_producer + " " + normalize(appellation_name) + " " + normalize(cuvee)).strip(),
        (lwin_producer + " " + normalize(cuvee) + " " + normalize(appellation_name)).strip(),
        (lwin_producer + " " + normalize(cuvee)).strip(),
    ]
    try:
        from rapidfuzz import fuzz
    except ImportError:  # in requirements-rp.txt
        logging.getLogger(__name__).warning("rapidfuzz isn't installed: no fuzzy LWIN suggestions")
        return []
    best = {}
    for entry in lwin_entries:
        dn = entry.get("display_name_norm") or ""
        if not dn:
            continue
        score = max(fuzz.ratio(n, dn) for n in names if n)
        if score >= threshold and score > best.get(entry["lwin"], (None, 0))[1]:
            best[entry["lwin"]] = (entry, score)
    ranked = sorted(best.values(), key=lambda x: -x[1])[:limit]
    return [(e, f"FUZZY ({s:.0f}%)", s) for e, s in ranked]


# --- An LWIN across the vintages of a cuvée (Settings › Maintenance) ---

def lwin7(lwin):
    """The wine's LWIN7 from any LWIN (LWIN11 adds the vintage, LWIN16/18 the format): the first 7 digits."""
    digits = re.sub(r"\D", "", str(lwin or ""))
    return digits[:7] if len(digits) >= 7 else None


def cuvee_key(wine):
    """The vintages that share an LWIN: same producer, cuvée, appellation and colour."""
    return wine.producer_id, (wine.cuvee or "").strip(), wine.appellation_id, wine.type or ""


def spread_lwin(session, commit=False, log=print):
    """Every wine without an LWIN whose other vintages (cuvee_key) have one, the same LWIN7 for all: it gets that
    LWIN7. ([(wine, lwin7)] filled or to fill, [(key, {lwin7: [wines]})] cuvées whose vintages disagree)."""
    families = {}
    for w in session.query(Wine).filter(Wine.producer_id != None).order_by(Wine.id):  # noqa: E711
        families.setdefault(cuvee_key(w), []).append(w)
    filled, conflicts = [], []
    for key, wines in families.items():
        codes = {}
        for w in wines:
            if lwin7(w.lwin):
                codes.setdefault(lwin7(w.lwin), []).append(w)
        if len(codes) > 1:
            conflicts.append((key, codes))
            continue
        if not codes:
            continue
        code = next(iter(codes))
        for w in wines:
            if not (w.lwin or "").strip():
                filled.append((w, code))
                log(f"wine {w.id} ({w.vintage or 'NV'}): {code}")
                w.lwin = code
    if commit:
        session.commit()
    else:
        session.rollback()
    return filled, conflicts


# --- Cellar wines without an LWIN (Settings › Maintenance) ---

# A fuzzy match is saved on its own only this close, and this far ahead of the next candidate: 95% and 5 points,
# or 90% and 10 points (Clos de Tart Grand Cru 94% against the domaine's Marc 83%)
AUTO_RULES = ((95, 5), (90, 10))
LWIN_COLOURS = {"red": "Red", "white": "White", "rose": "Rose", "rosé": "Rose"}


def missing_lwin(session):
    """Wines with bottles in the cellar and no LWIN, newest first."""
    return (session.query(Wine)
            .join(Bottle, Bottle.wine_id == Wine.id)
            .filter((Wine.lwin == None) | (Wine.lwin == ""))  # noqa: E711
            .filter(Wine.producer_id != None, Bottle.qty > 0)  # noqa: E711
            .distinct().order_by(Wine.id.desc()).all())


def _same_colour(wine, entry):
    want = LWIN_COLOURS.get((wine.type or "").lower())
    return not want or entry.get("colour") in (want, "Mixed", "NA", "", None)


def _sibling_lwin(session, wine):
    """The LWIN of another vintage of the same cuvée (LWIN7 is the same for every vintage)."""
    for other in session.query(Wine).filter(Wine.producer_id == wine.producer_id, Wine.id != wine.id,
                                            Wine.lwin != None, Wine.lwin != ""):  # noqa: E711
        if ((other.cuvee or "") == (wine.cuvee or "") and other.appellation_id == wine.appellation_id
                and (other.type or "") == (wine.type or "")):
            return other.lwin
    return None


def _strict(entry, cuvee, appellation):
    """The Liv-ex wine name is the cuvée, alone or with the appellation (find_exact_match also takes substrings)."""
    names = set()
    for norm in (normalize_light, normalize):
        for text in (cuvee, f"{appellation} {cuvee}", f"{cuvee} {appellation}"):
            if text.strip():
                names.add(norm(text.strip()))
    return bool(names & {entry.get("wine_norm_light"), entry.get("wine_norm")})


def fill_missing_lwin(session, commit=False, log=print, db_path=None):
    """Proposes an LWIN for each cellar wine without one, and with commit saves the confident ones: another vintage
    of the same cuvée has one, the Liv-ex wine name is the cuvée (with or without the appellation), or a fuzzy match high enough and well ahead of the next (AUTO_RULES).
    [(wine, status, candidates)] with status "saved"/"sure" (saved when committing), "check" or "none";
    candidates [(entry, match type, score)]. FileNotFoundError without the index."""
    db_path = db_path or entries_for.__defaults__[0]
    if not os.path.exists(db_path):
        raise FileNotFoundError(db_path)
    results = []
    for wine in missing_lwin(session):
        label = " ".join(x for x in (wine.producer.name, wine.cuvee or "",
                                     wine.appellation.name if wine.appellation else "", wine.vintage or "") if x)
        sibling = _sibling_lwin(session, wine)
        if sibling:
            found, sure = [({"lwin": sibling, "display_name": "the LWIN of another vintage", "colour": None},
                            "VINTAGE", 100)], True
        else:
            appellation = wine.appellation.name if wine.appellation else ""
            entries = [e for e in entries_for(wine.producer.name, db_path) if _same_colour(wine, e)]
            found = suggest(entries, wine.producer.name, wine.cuvee or "", appellation)
            lead = found[0][2] - found[1][2] if len(found) > 1 else 100
            sure = bool(found) and (_strict(found[0][0], wine.cuvee or "", appellation) or any(
                found[0][2] >= score and lead >= margin for score, margin in AUTO_RULES))
        if sure:
            status = "saved" if commit else "sure"
            if commit:
                wine.lwin = found[0][0]["lwin"]
                session.commit()
            log(f"{'✅' if commit else '→ '} {label}: {found[0][0]['lwin']} {found[0][0]['display_name']}")
        elif found:
            status = "check"
            log(f"?  {label}: {', '.join(e['lwin'] for e, _, _ in found)} — pick it in the wine form")
        else:
            status = "none"
            log(f"–  {label}: no match")
        results.append((wine, status, found))
    return results


# --- Main ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="The Liv-ex LWIN list, prepared for the app's LWIN suggestions.")
    parser.add_argument("--preprocess", action="store_true", help="Convert LWINdatabase.xlsx to lwin_lookup.json (run once).")
    parser.add_argument("--build-index", action="store_true", help="Build data/lwin/lwin.sqlite from lwin_lookup.json (for the app).")
    args = parser.parse_args()
    if args.preprocess:
        preprocess_lwin()
    if args.build_index:
        build_index()
    if not (args.preprocess or args.build_index):
        parser.print_help()
