"""Your wines and the cadastre's lieux-dits (the store's lieu_dit source: geo_scripts/etl_lieux_dits.py): a cuvée whose
name holds a lieu-dit eligible for its appellation ("Le Bourg", Saumur-Champigny) is linked to it. The lieu-dit
becomes a vineyard (the vineyards table, boundary "lieu_dit:<commune>:<slug>"), named as on the label (its accents),
its village from the cadastre; every vintage of the cuvée gets it.

Settings › Maintenance › Lieux-dits for your wines: a preview of the matches to tick, then the ticked ones linked.
"""
import json
import re
import unicodedata
from collections import defaultdict

from sqlalchemy.orm import joinedload

import geo
from models import Vineyard, Wine

ARTICLES = {"le", "la", "les", "l", "au", "aux", "du", "de", "des", "d", "en", "sur", "sous"}
MIN_LETTERS = 4  # "Clos", "Bois": shorter cores match too much
# What else a cuvée's name can say beside its lieu-dit ("Clos des Carmes", "Treilles Partie Haute", "La Charpentrie
# Blanc"): any other word means the lieu-dit is only part of the name ("Bonnes Blanches" isn't "Les Blanches")
GENERIC = ARTICLES | {"clos", "cuvee", "blanc", "blanche", "rouge", "rose", "sec", "doux", "demi", "liquoreux",
                      "moelleux", "vieilles", "vieille", "vignes", "vv", "partie", "haute", "haut", "basse", "bas",
                      "gauche", "droite", "grand", "grande", "vin", "cru", "premier", "1er", "et", "a"}
SURE_VINES = 0.5  # a lieu-dit mostly in vines: ticked when it's the only one


def _fold_char(c):
    f = unicodedata.normalize("NFKD", c).encode("ascii", "ignore").decode().lower()
    return f if len(f) == 1 else c.lower()  # one for one: the folded text lines up with the original


def fold(s):
    """Lower case, no accents, the same length as s (to find a match's span in the original)"""
    return "".join(_fold_char(c) for c in s or "")


def words(s):
    return re.findall(r"[a-z0-9]+", fold(s))


def same(w):
    """A word without its plural's s or x: the label's "Les Chétillons" is the cadastre's "Chétillon" """
    return w[:-1] if len(w) > 3 and w[-1] in "sx" else w


def core(tokens):
    """A name's words without its leading articles: "Les Poyeux" -> ["poyeux"]"""
    i = 0
    while i < len(tokens) - 1 and tokens[i] in ARTICLES:
        i += 1
    return tokens[i:]


def _index():
    """{appellation (folded): [(store id, name, details, core words)]} for the store's lieux-dits"""
    found = geo._lieux_dits()
    if found is None:
        return None
    ids, names, details, _, _ = found
    out = defaultdict(list)
    for sid, name, d in zip(ids, names, details):
        d = json.loads(d) if d else {}
        c = core(words(name))
        if not c or len("".join(c)) < MIN_LETTERS:
            continue
        for aoc in (d.get("aocs") or "").split("; "):
            if aoc:
                out[" ".join(words(aoc))].append((sid, name, d, c))
    return out


def _at(hay, needle):
    """Where needle's words are in hay, or -1"""
    needle = [same(w) for w in needle]
    return next((i for i in range(len(hay) - len(needle) + 1) if [same(w) for w in hay[i:i + len(needle)]] == needle), -1)


def _matches(cuvee_words, name_words, core_words):
    """Whether the cuvée names this lieu-dit, and how well: 2 its whole name ("Sur les Pouches"), 1 its name
    without the articles ("Pouches"), 0 not (or the rest of the cuvée's name isn't generic)"""
    for whole, needle in ((2, name_words), (1, core_words)):
        i = _at(cuvee_words, needle)
        if i >= 0 and all(w in GENERIC for w in cuvee_words[:i] + cuvee_words[i + len(needle):]):
            return whole
    return 0


def span(cuvee, name):
    """The lieu-dit's name as the label writes it ("Les Gravières" for the cadastre's "Les Gravieres"), else None"""
    pattern = r"[\s'’-]+".join(re.escape(same(w)) + "[sx]?" for w in words(name))
    m = re.search(rf"(?<![a-z0-9]){pattern}(?![a-z0-9])", fold(cuvee))
    return cuvee[m.start():m.end()] if m else None


def candidates(session):
    """[(the cuvée's wines, [(store id, name, details)])]: the cuvées without a vineyard named after a lieu-dit eligible
    for their appellation (the rest of the name generic: "Clos des Carmes", "La Charpentrie Blanc"), those naming its
    whole name first ("Sur les Pouches" over "Les Pouches" for "Sur les Pouches"), the most in vines first."""
    index = _index()
    if index is None:
        return None
    wines = (session.query(Wine).options(joinedload(Wine.producer), joinedload(Wine.appellation))
             .filter(Wine.vineyard_id.is_(None), Wine.appellation_id.isnot(None), Wine.cuvee.isnot(None), Wine.cuvee != "")
             .all())
    cuvees = defaultdict(list)  # a cuvée: same producer, name and appellation
    for w in wines:
        cuvees[(w.producer_id, w.cuvee.strip().lower(), w.appellation_id)].append(w)
    out = []
    for group in cuvees.values():
        w = group[0]
        lieux = index.get(" ".join(words(w.appellation.name)), [])
        cw = words(w.cuvee)
        found = [(sid, name, d, q) for sid, name, d, c in lieux if (q := _matches(cw, words(name), c))]
        if not found:
            continue
        best = max(q for *_, q in found)  # the whole name when one is
        found = [(sid, name, d) for sid, name, d, q in found if q == best]
        out.append((sorted(group, key=lambda x: x.vintage or ""), sorted(found, key=lambda f: -(f[2].get("vines") or 0))))
    return sorted(out, key=lambda x: (x[0][0].producer.name if x[0][0].producer else "", x[0][0].cuvee))


def sure(options):
    """Ticked in the preview: the only lieu-dit it can be, mostly in vines"""
    return len(options) == 1 and (options[0][2].get("vines") or 0) >= SURE_VINES


def vineyard(session, sid, name, details, region_id=None, label=None):
    """The lieu-dit as a vineyard: the one made before, else a new one (named `label`, the wine's spelling, when
    given)"""
    boundary = f"lieu_dit:{sid}"
    v = session.query(Vineyard).filter(Vineyard.boundary == boundary).first()
    if v is None:
        v = Vineyard(name=label or name, region_id=region_id, village=details.get("commune_name"), boundary=boundary)
        session.add(v)
        session.flush()
    return v


def link(session, wines, sid, name, details):
    """The lieu-dit as a vineyard (made once, then reused), on these wines."""
    w = wines[0]
    region_id = w.region_id or (w.appellation.region_id if w.appellation else None)
    v = vineyard(session, sid, name, details, region_id, span(w.cuvee, name))
    for w in wines:
        w.vineyard_id = v.id
    return v


_folded = {}  # the store's names as words, worked out once per store read


def _fold(found):
    """The names' words, worked out once per store read (a second or two for 90,000): search's index"""
    if _folded.get("of") is not found:
        _folded.update({"of": found, "words": [{same(w) for w in words(n)} for n in found[1]]})


def warm():
    """search's index made ahead of the first search (geo.warm, in the background at startup)"""
    found = geo._lieux_dits()
    if found is not None:
        _fold(found)


def search(q, limit=15):
    """[(store id, name, details)] whose name has every word of q, the most in vines first"""
    found = geo._lieux_dits()
    want = [same(w) for w in core(words(q))]  # "les chetillons" finds "Chétillon"
    if found is None or not want:
        return []
    ids, names, dets, _, _ = found
    _fold(found)
    hits = [(ids[i], names[i], json.loads(dets[i]) if dets[i] else {})
            for i, ws in enumerate(_folded["words"]) if all(w in ws for w in want)]
    return sorted(hits, key=lambda h: -(h[2].get("vines") or 0))[:limit]


def find(sid):
    """(name, details) of one lieu-dit in the store, or None"""
    found = geo._lieux_dits()
    if found is None:
        return None
    ids, names, dets, _, _ = found
    i = geo._lieu_pos().get(sid)
    if i is None:
        return None
    return names[i], (json.loads(dets[i]) if dets[i] else {})


def outline(sid):
    """(name, details, GeoJSON geometry text) of one lieu-dit in the store, or None"""
    found = geo._lieux_dits()
    if found is None:
        return None
    ids, names, dets, geoms, _ = found
    i = geo._lieu_pos().get(sid)
    if i is None:
        return None
    return names[i], (json.loads(dets[i]) if dets[i] else {}), geoms[i]


def details(boundary):
    """A lieu-dit vineyard's details from the store: {"name" (the cadastre's), "village", "aocs" [...], "vines"}; None
    for another boundary or one the store doesn't have"""
    if not boundary or not boundary.startswith("lieu_dit:"):
        return None
    found = geo._lieux_dits()
    if found is None:
        return None
    ids, names, dets, _, _ = found
    sid = boundary.split(":", 1)[1]
    i = geo._lieu_pos().get(sid)
    if i is None:
        return None
    d = json.loads(dets[i]) if dets[i] else {}
    return {"name": names[i], "village": d.get("commune_name"), "aocs": [a for a in (d.get("aocs") or "").split("; ") if a],
            "vines": d.get("vines")}
