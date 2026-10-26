"""The grape varieties (docs/reference-data.md): the notable ones, named as wine people name them, with their common synonyms as aliases.

- Which: every grape variety on Wikidata (CC0) with an English Wikipedia article (~680), listed with
  fetch_wikidata() into data/geo/wikidata/grapes.json (its names in a dozen languages, and its VIVC number, P3904).
- Named by its English name (Wikidata's: Grenache, not VIVC's GARNACHA TINTA); checked against VIVC, the Vitis
  International Variety Catalogue (JKI): its passport page gives the prime name and every synonym (cached in
  data/geo/vivc/).
- Aliases: VIVC's prime name, and those of its synonyms in established use: also the variety's name in another
  language on Wikidata (Spätburgunder, Pinot Nero, Garnacha), or in COMMON (the synonyms wine lists use: Tinta Roriz, Jaen,
  Monastrell...) when VIVC confirms them; VIVC's hundreds of others (shared, local, obsolete) would match the wrong
  grape.
- A variety without a VIVC number on Wikidata is looked up on VIVC by name (its prime name, else a synonym only one
  variety has).
- EXTRA: varieties the wines need that the notable list lacks (Terrantez do Pico, Manteúdo...), by VIVC name;
  RENAMES: Touriga Francesa is Touriga Franca today, Doña Blanca Síria (VIVC's prime name).
- Every grape gets what VIVC says of it, where it was empty: its berries' colour, its country of origin, its VIVC
  number and its parents (VIVC's parents replace any others it disagrees with) (named as the list names them: Gouais Blanc, Pinot), for the grapes page's family graph.
- A variety the database has (by name or alias) gets the aliases it lacks; one it hasn't is added; duplicates
  (MERGES: Pinot Grigio is Pinot Gris) are merged, their wines moved and the name kept as an alias.

A dry run unless --commit; the report goes to data/reference_build/grapes.txt.

    python scripts/reference/grapes.py            # dry run (fetches what isn't cached: ~1 VIVC page a second)
    python scripts/reference/grapes.py --commit   # after a backup
"""
import argparse
import collections
import html
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
from winelib_utils import USER_AGENT  # noqa: E402
GEO = os.getenv("GEO_DIR", os.path.join(ROOT, "data", "geo"))
WIKIDATA = os.path.join(GEO, "wikidata", "grapes.json")
VIVC_DIR = os.path.join(GEO, "vivc")
REPORT = os.path.join(ROOT, "data", "reference_build", "grapes.txt")
HEADERS = {"User-Agent": USER_AGENT}
WD_API = "https://www.wikidata.org/w/api.php"
VIVC_PAGE = "https://www.vivc.de/index.php?r=passport%2Fview&id={}"
LANGS = ["en", "fr", "de", "it", "es", "pt", "ca", "hu", "el", "hr", "sl"]
# Varieties the wines need that aren't notable enough for Wikidata's list (no English Wikipedia article): looked up
# on VIVC by name; one VIVC files under a variety the database has becomes its alias
EXTRA = ["Terrantez do Pico", "Manteúdo", "Cerceal Branco", "Malvasia Fina", "Tinta Pinheira", "Alicante Branco",
         "Diagalves", "Olho de Lebre", "Tamarez", "Merwah"]
# Aliases given by hand, whatever VIVC lists (a regional name a label uses: Morillon is Styria's Chardonnay)
EXTRA_ALIASES = {"Chardonnay": ["Morillon", "Melon à Queue Rouge"]}
# Names changed to the one the wine world uses today (the old name stays an alias)
RENAMES = {"Touriga Francesa": "Touriga Franca", "Doña Blanca": "Síria"}
# Duplicates in the database, one variety under two names: dropped -> kept (wines moved, the name an alias)
MERGES = {"Pinot Grigio": "Pinot Gris", "Ugni Blanc": "Trebbiano"}
# Not grapes: a blend isn't a variety (docs/history/blends.md)
NOT_GRAPES = {"field blend"}
VIVC_SEARCH = ("https://www.vivc.de/index.php?r=cultivarname%2Findex&CultivarnameSearch%5Bcultivarnames%5D=cultivarn"
               "&CultivarnameSearch%5Btext%5D={}")
# The synonyms wine lists and labels use, by the grape's English name: aliases when VIVC lists them for it
COMMON = {
    "Tempranillo": ["Tinta Roriz", "Aragonez", "Tinto Fino", "Tinta del País", "Tinta de Toro", "Ull de Llebre", "Cencibel"],
    "Mencía": ["Jaen"],
    "Syrah": ["Shiraz"],
    "Mourvèdre": ["Monastrell", "Mataro"],
    "Grenache": ["Garnacha", "Cannonau", "Garnatxa"],
    "Carignan": ["Cariñena", "Mazuelo", "Samsó", "Carignano"],
    "Pinot noir": ["Spätburgunder", "Pinot Nero", "Blauburgunder"],
    "Pinot gris": ["Grauburgunder", "Pinot Grigio", "Ruländer"],
    "Pinot blanc": ["Weissburgunder", "Pinot Bianco"],
    "Pinot Meunier": ["Meunier", "Schwarzriesling", "Müllerrebe"],
    "Trebbiano": ["Ugni Blanc"],
    "Sangiovese": ["Brunello", "Prugnolo Gentile", "Morellino", "Nielluccio"],
    "Malbec": ["Côt", "Auxerrois"],
    "Cabernet Franc": ["Bouchet", "Breton"],
    "Chenin blanc": ["Pineau de la Loire", "Steen"],
    "Savagnin": ["Traminer", "Naturé"],
    "Vermentino": ["Rolle", "Favorita", "Pigato"],
    "Nebbiolo": ["Spanna", "Chiavennasca"],
    "Zinfandel": ["Primitivo", "Crljenak Kaštelanski", "Tribidrag"],
    "Friulano": ["Tai", "Sauvignonasse"],
    "Blaufränkisch": ["Lemberger", "Kékfrankos", "Frankovka"],
    "Graciano": ["Tintilla", "Morrastel"],
    "Albariño": ["Alvarinho"],
    "Godello": ["Gouveio"],
    "Macabeo": ["Viura"],
    "Xarel·lo": ["Pansa Blanca"],
    "Muscat blanc à petits grains": ["Moscato Bianco", "Muscat de Frontignan", "Muskateller", "Moscatel Galego"],
    "Muscat of Alexandria": ["Moscatel de Alejandría", "Zibibbo"],
    "Trousseau": ["Bastardo"],
    "Tinta Amarela": ["Trincadeira"],
    "Castelão": ["Periquita"],
    "Fernão Pires": ["Maria Gomes"],
    "Síria": ["Roupeiro", "Códega"],
    "Alicante Bouschet": ["Garnacha Tintorera"],
    "Cinsaut": ["Cinsault"],
    "Sémillon": ["Semillon"],
    "Gewürztraminer": ["Traminer Aromatico"],
    "Grüner Veltliner": ["Weissgipfler"],
    "Melon de Bourgogne": ["Muscadet"],
    "Rkatsiteli": ["Rkaziteli"],
    "Welschriesling": ["Graševina", "Olaszrizling", "Riesling Italico"],
}


def common_by_key():
    return {norm(k): v for k, v in COMMON.items()}


def norm(text):
    t = "".join(c for c in unicodedata.normalize("NFKD", str(text or "")).casefold() if not unicodedata.combining(c))
    return " ".join(re.findall(r"\w+", t))


def get_json(url, params):
    req = urllib.request.Request(url + "?" + urllib.parse.urlencode({**params, "format": "json"}), headers=HEADERS)
    for attempt in range(6):
        try:
            return json.load(urllib.request.urlopen(req, timeout=60))
        except Exception:
            time.sleep(10 * (attempt + 1))
    raise RuntimeError(f"Wikidata didn't answer: {params}")


def fetch_wikidata():
    """data/geo/wikidata/grapes.json: every item that is an instance of grape variety (Q958314), with its names,
    English Wikipedia article and VIVC number."""
    ids, offset = [], 0
    while offset is not None:
        d = get_json(WD_API, {"action": "query", "list": "search", "srsearch": "haswbstatement:P31=Q958314",
                              "srnamespace": 0, "srlimit": 500, "sroffset": offset, "srprop": ""})
        ids += [x["title"] for x in d["query"]["search"]]
        offset = d.get("continue", {}).get("sroffset")
    out = []
    for i in range(0, len(ids), 50):
        d = get_json(WD_API, {"action": "wbgetentities", "ids": "|".join(ids[i:i + 50]),
                              "props": "labels|aliases|sitelinks|claims", "languages": "|".join(LANGS),
                              "sitefilter": "enwiki"})
        for q, e in d.get("entities", {}).items():
            labels = [v["value"] for v in e.get("labels", {}).values()]
            names = labels + [a["value"] for v in e.get("aliases", {}).values() for a in v]
            vivc = [c["mainsnak"].get("datavalue", {}).get("value") for c in e.get("claims", {}).get("P3904", [])]
            out.append({"id": q, "name": e.get("labels", {}).get("en", {}).get("value"),
                        "enwiki": e.get("sitelinks", {}).get("enwiki", {}).get("title"),
                        "vivc": next((v for v in vivc if v), None), "names": list(dict.fromkeys(names)),
                        "labels": list(dict.fromkeys(labels))})
        time.sleep(1)
    os.makedirs(os.path.dirname(WIKIDATA), exist_ok=True)
    with open(WIKIDATA, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=0)
    return out


def vivc_passport(number):
    """{"prime", "colour", "origin", "synonyms"} from VIVC's passport page (cached), or None."""
    path = os.path.join(VIVC_DIR, f"{number}.html")
    if not os.path.exists(path):
        req = urllib.request.Request(VIVC_PAGE.format(number), headers=HEADERS)
        try:
            page = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
        except Exception:
            return None
        os.makedirs(VIVC_DIR, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(page)
        time.sleep(1)  # politely
    page = open(path, encoding="utf-8").read()
    fields = {}
    for k, v in re.findall(r"<tr[^>]*>\s*<th[^>]*>(.*?)</th>\s*<td[^>]*>(.*?)</td>", page, re.S):
        k = re.sub(r"<[^>]+>", "", k).strip()
        fields.setdefault(k, html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", v))).strip())
    if not fields.get("Prime name"):
        return None
    synonyms = []
    i = page.find("Synonyms:")
    if i >= 0:
        block = page[i:page.find("</table>", i) if page.find("</table>", i) > 0 else i + 200000]
        # each synonym a cell, plain or a link to its literature
        cells = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", block, re.S)]
        synonyms = [c for c in cells if c and not c.isdigit() and not c.startswith("Synonyms") and len(c) < 60]
    parents = [fields.get("Prime name of parent 1"), fields.get("Prime name of parent 2")]
    return {"prime": fields["Prime name"], "colour": fields.get("Color of berry skin"),
            "origin": fields.get("Country or region of origin of the variety"), "synonyms": synonyms,
            "number": int(fields["Variety number VIVC"]) if (fields.get("Variety number VIVC") or "").isdigit() else None,
            "parents": [p for p in map(parent_name, parents) if p]}


# VIVC's pedigrees name Pinot Noir "Pinot" (the variety's group): the list's name for it
PARENT_NAMES = {"pinot": "Pinot Noir"}


def parent_name(text):
    """A parent's name as VIVC gives it, or None: not "?", not a note ("See below: bibliography..."), not an unnamed
    cross ("AVARENGO X BOTTAGERA (FALSE)"); "SAVAGNIN = TRAMINER" is Savagnin."""
    t = (text or "").strip()
    if not t or t == "?" or t.lower().startswith(("see below", "different propositions")) or re.search(r"\sX\s", t):
        return None
    return t.split("=")[0].strip() or None


def umlauts(text):
    """VIVC writes umlauts out (OESTERREICHISCH WEISS): the key both spellings share"""
    t = str(text or "").lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        t = t.replace(a, b)
    return norm(t)


def vivc_search(name):
    """A VIVC variety number by name: the variety whose prime name it is, else the only one that has it as a
    synonym; None when there's none, or several (cached in data/geo/vivc/search/)."""
    import hashlib
    key = hashlib.sha1(norm(name).encode()).hexdigest()[:16]
    path = os.path.join(VIVC_DIR, "search", f"{key}.html")
    if not os.path.exists(path):
        query = urllib.parse.quote(re.sub(r"[^\w '-]", " ", name).upper().strip())
        req = urllib.request.Request(VIVC_SEARCH.format(query), headers=HEADERS)
        try:
            page = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
        except Exception:
            return None
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(page)
        time.sleep(1)
    page = open(path, encoding="utf-8").read()
    # each row: the cultivar name found, its prime name, its variety number, species, colour, country
    exact, by_synonym = set(), set()
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S):
        cells = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
        if len(cells) < 3 or not cells[2].isdigit():
            continue
        cultivar, prime, number = cells[0], cells[1], cells[2]
        if norm(prime) == norm(name):
            exact.add(number)
        elif norm(cultivar) == norm(name):
            by_synonym.add(number)
    found = exact or by_synonym
    return next(iter(found)) if len(found) == 1 else None


def title(name):
    """VIVC's capitals as a name: PINOT NOIR -> Pinot Noir, NERO D'AVOLA -> Nero d'Avola."""
    small = {"de", "di", "d", "del", "della", "du", "des", "la", "le", "da", "do", "dos", "y", "e", "et"}
    words = re.split(r"(\s+|-)", name.lower())
    out = []
    for i, w in enumerate(words):
        if "'" in w:
            a, b = w.split("'", 1)
            w = (a if a in small and i else a.capitalize()) + "'" + b.capitalize()
        elif w and not w.isspace() and w != "-" and not (w in small and i):
            w = w.capitalize()
        out.append(w)
    return "".join(out)


COLOURS = {"BLANC": "White", "NOIR": "Red", "ROUGE": "Red", "ROSE": "Pink", "GRIS": "Grey"}


DIFFERS = []  # (grape, its parents, VIVC's): parents set already that VIVC names otherwise: VIVC's win


def facts(session, grapes, new):
    """[(Varietal or new grape dict, {column: value})]: what VIVC says of each grape, where the column is empty."""
    from winelib_utils.models import Varietal
    by_label = {}
    for g in grapes:
        if g.get("vivc"):
            for n in [g["name"] or "", *g.get("labels", [])]:
                if n:
                    by_label.setdefault(norm(n), g["vivc"])
    rows = [*session.query(Varietal), *new]
    names = {}
    for r in rows:
        name, aliases = (r.name, r.aliases) if isinstance(r, Varietal) else (r["name"], ", ".join(r["aliases"]))
        for n in [name, *(aliases or "").split(",")]:
            if n.strip():
                names.setdefault(norm(n), name)
                names.setdefault(umlauts(n), name)
    out = []
    for r in rows:
        name, aliases = (r.name, r.aliases) if isinstance(r, Varietal) else (r["name"], ", ".join(r["aliases"]))
        passport = r["passport"] if isinstance(r, dict) else None
        if passport is None:
            number = next((by_label[k] for k in [norm(name), *map(norm, (aliases or "").split(","))] if k in by_label),
                          None) or vivc_search(name)
            passport = vivc_passport(number) if number else None
        if not passport:
            continue
        values = {"color": COLOURS.get((passport["colour"] or "").upper()),
                  "origin": title(passport["origin"]) if passport.get("origin") else None,
                  "vivc": passport.get("number"),
                  "parents": ", ".join(PARENT_NAMES.get(norm(p)) or names.get(norm(p)) or names.get(umlauts(p)) or title(p)
                                       for p in passport["parents"]) or None}
        current = {k: getattr(r, k) for k in values} if isinstance(r, Varietal) else {}
        changes = {k: v for k, v in values.items() if v and not current.get(k)}
        as_set = lambda s: {umlauts(x) for x in (s or "").split(",") if x.strip()}  # noqa: E731
        if values["parents"] and current.get("parents") and as_set(values["parents"]) != as_set(current["parents"]):
            DIFFERS.append((name, current["parents"], values["parents"]))
            changes["parents"] = values["parents"]  # VIVC's (DNA-confirmed) win over the profiles' notes
        if changes:
            out.append((r, changes))
    return out


def plan(session):
    from winelib_utils.models import Varietal, Wine
    merged = []
    for drop, keep in MERGES.items():
        d = session.query(Varietal).filter(Varietal.name == drop).one_or_none()
        k = session.query(Varietal).filter(Varietal.name == keep).one_or_none()
        if d and k:
            merged.append((d, k, session.query(Wine).filter(Wine.varietal_id == d.id).count()))
    dropped = {d.id for d, _, _ in merged}
    grapes = json.load(open(WIKIDATA, encoding="utf-8")) if os.path.exists(WIKIDATA) else fetch_wikidata()
    if any("labels" not in g for g in grapes):  # an older listing
        grapes = fetch_wikidata()
    global COMMON_BY_KEY
    COMMON_BY_KEY = common_by_key()
    have = {}
    for v in session.query(Varietal):
        if v.id in dropped:
            continue
        for n in [v.name, *(v.aliases or "").split(",")]:
            if n.strip():
                have.setdefault(norm(n), v)
    for d, k, _ in merged:  # the dropped name finds the kept grape
        have.setdefault(norm(d.name), k)
    new, aliased, unmatched, seen = [], [], [], set()
    for g in sorted((g for g in grapes if g["enwiki"] and g["name"]), key=lambda g: g["name"].lower()):
        if norm(g["name"]) in NOT_GRAPES:
            continue
        number = g.get("vivc") or vivc_search(g["name"])
        passport = vivc_passport(number) if number else None
        if not passport:
            unmatched.append(g)
            continue
        if passport["prime"] in seen:  # two Wikidata items for one variety (a colour mutation's page...)
            continue
        seen.add(passport["prime"])
        name = title(g["name"]) if g["name"] == g["name"].lower() or " " in g["name"] else g["name"]
        wd = {norm(n) for n in g["labels"]}  # its names in other languages, not Wikidata's free-form aliases
        vivc_names = {norm(s): s for s in [passport["prime"], *passport["synonyms"]]}
        # VIVC writes umlauts as AE, OE, UE (RULAENDER): Ruländer is that one
        vivc_names.update({norm(re.sub(r"AE|OE|UE", lambda m: m.group(0)[0], s.upper())): s
                           for s in [passport["prime"], *passport["synonyms"]]})
        common = [title(s) for s in passport["synonyms"] if norm(s) in wd]
        listed = [c for k in {norm(g["name"]), norm(name), norm(passport["prime"])} for c in COMMON_BY_KEY.get(k, [])]
        common += [c for c in dict.fromkeys(listed) if norm(c) in vivc_names]
        # one spelling per alias: the hand list's (Ruländer) over VIVC's capitals (RULANDER)
        by_key = {}
        for x in [title(passport["prime"]), *common]:
            if norm(x) != norm(name) and (norm(x) not in by_key or not x.isascii()):
                by_key[norm(x)] = x
        aliases = list(by_key.values())
        existing = next((have[k] for k in [norm(name), *map(norm, aliases)] if k in have), None)
        if existing:
            mine = {norm(x) for x in [existing.name, *(existing.aliases or "").split(",")] if x.strip()}
            missing = [a for a in aliases + ([name] if norm(name) not in mine else []) if norm(a) not in mine]
            if missing:
                aliased.append((existing, missing, passport))
        else:
            new.append({"name": name, "aliases": aliases, "passport": passport, "wikidata": g["id"]})
            for k in [norm(name), *map(norm, aliases)]:
                have.setdefault(k, None)
    # an alias that is another grape's name, or that two grapes claim, would match the wrong one: dropped
    names = {norm(v.name) for v in session.query(Varietal) if v.id not in dropped} | {norm(g["name"]) for g in new}
    claims = collections.Counter(norm(a) for g in new for a in g["aliases"])
    claims.update(norm(a) for _, missing, _ in aliased for a in missing)
    ok = lambda a, own: norm(a) == norm(own) or (norm(a) not in names and claims[norm(a)] <= 1)  # noqa: E731
    for g in new:
        g["aliases"] = [a for a in g["aliases"] if ok(a, g["name"])]
    aliased = [(v, kept, pp) for v, missing, pp in aliased
               if (kept := [a for a in missing if ok(a, v.name)])]
    # the extra varieties
    for name in EXTRA:
        if norm(name) in have:
            continue
        number = vivc_search(name)
        passport = vivc_passport(number) if number else None
        if not passport:
            unmatched.append({"name": name, "id": "VIVC: no single match"})
            continue
        owner = have.get(norm(passport["prime"])) or next((g for g in new if norm(g["name"]) == norm(title(passport["prime"]))
                                                           or norm(passport["prime"]) in map(norm, g["aliases"])), None)
        if isinstance(owner, Varietal):
            aliased.append((owner, [name], passport))
        elif owner is not None:
            owner["aliases"].append(name)
        else:
            aliases = [title(passport["prime"])] if norm(passport["prime"]) != norm(name) else []
            new.append({"name": name, "aliases": aliases, "passport": passport, "wikidata": None})
        have.setdefault(norm(name), owner if isinstance(owner, Varietal) else None)
    for grape, extra in EXTRA_ALIASES.items():
        row = session.query(Varietal).filter(Varietal.name == grape).one_or_none()
        if row is not None:
            mine = {norm(x) for x in [row.name, *(row.aliases or "").split(",")] if x.strip()}
            missing = [a for a in extra if norm(a) not in mine]
            if missing:
                aliased.append((row, missing, None))
    renamed = []
    for old, new_name in RENAMES.items():
        row = session.query(Varietal).filter(Varietal.name == old).one_or_none()
        if row is not None and not session.query(Varietal).filter(Varietal.name == new_name).count():
            renamed.append((row, new_name))
        for g in new:
            if g["name"] == old:
                g["aliases"] = [a for a in g["aliases"] if norm(a) != norm(new_name)] + [old]
                g["name"] = new_name
    return {"new": new, "aliased": aliased, "unmatched": unmatched, "merged": merged, "renamed": renamed,
            "facts": facts(session, grapes, new)}


def report(p):
    out = ["Grape varieties (Wikidata's notable ones, checked against VIVC)", "",
           f"Duplicates merged: {len(p['merged'])}"] + [f"  {d.name} -> {k.name} ({n} wines)" for d, k, n in p["merged"]] + ["",
           f"Renamed: {len(p.get('renamed', []))}"] + [f"  {v.name} -> {n}" for v, n in p.get("renamed", [])] + ["",
           f"Aliases added to grapes already there: {len(p['aliased'])}"]
    out += [f"  {v.name}: + {', '.join(a)}" for v, a, _ in p["aliased"]]
    out += ["", f"New grapes: {len(p['new'])}"]
    out += [f"  {g['name']}" + (f" (also {', '.join(g['aliases'])})" if g["aliases"] else "")
            + f" [{(g['passport']['colour'] or '').lower()}, {(g['passport']['origin'] or '?').title()}]" for g in p["new"]]
    with_parents = [(r, c) for r, c in p.get("facts", []) if c.get("parents")]
    out += ["", f"VIVC's facts filled (colour, origin, number, parents): {len(p.get('facts', []))} grapes, "
                f"{len(with_parents)} with their parents"]
    out += [f"  {(r.name if hasattr(r, 'name') else r['name'])}: {c['parents']}" for r, c in with_parents[:60]]
    out += ["", f"Parents VIVC names otherwise (replaced by VIVC's): {len(DIFFERS)}"]
    out += [f"  {n}: {mine}  (VIVC: {theirs})" for n, mine, theirs in DIFFERS]
    out += ["", f"Not found on VIVC (no number on Wikidata, no single match by name; left out): {len(p['unmatched'])}"]
    out += [f"  {g['name']} ({g['id']})" for g in p["unmatched"]]
    return out


def apply(session, p):
    from winelib_utils.models import Varietal, Wine
    for d, k, _ in p["merged"]:
        session.query(Wine).filter(Wine.varietal_id == d.id).update({Wine.varietal_id: k.id})
        from winelib_utils.models import WineGrape
        has_kept = {wid for (wid,) in session.query(WineGrape.wine_id).filter(WineGrape.varietal_id == k.id)}
        for row in session.query(WineGrape).filter(WineGrape.varietal_id == d.id):
            if row.wine_id in has_kept:
                session.delete(row)  # already has the kept grape
            else:
                row.varietal_id = k.id
        aliases = [x.strip() for x in (k.aliases or "").split(",") if x.strip()]
        k.aliases = ", ".join(dict.fromkeys(aliases + [d.name, *(x.strip() for x in (d.aliases or "").split(",") if x.strip())]))
        session.delete(d)
    session.flush()
    for v, missing, _ in p["aliased"]:
        aliases = [x.strip() for x in (v.aliases or "").split(",") if x.strip()]
        v.aliases = ", ".join(dict.fromkeys(aliases + missing))
    for v, new_name in p.get("renamed", []):
        aliases = [x.strip() for x in (v.aliases or "").split(",") if x.strip() and x.strip() != new_name]
        v.aliases = ", ".join(dict.fromkeys(aliases + [v.name]))
        v.name = new_name
    session.flush()
    added = {}
    for g in p["new"]:
        added[g["name"]] = Varietal(name=g["name"], aliases=", ".join(g["aliases"]) or None)
        session.add(added[g["name"]])
    for r, changes in p.get("facts", []):
        row = added.get(r["name"]) if isinstance(r, dict) else r
        for k, v in changes.items():
            setattr(row, k, v)


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
        os.makedirs(os.path.dirname(REPORT), exist_ok=True)
        with open(REPORT, "w", encoding="utf-8") as f:
            f.write("\n".join(report(p)) + "\n")
        print(f"{len(p['new'])} new grapes; {len(p['aliased'])} given aliases; {len(p['unmatched'])} not on VIVC. "
              f"Report: {os.path.relpath(REPORT, ROOT)}")
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
