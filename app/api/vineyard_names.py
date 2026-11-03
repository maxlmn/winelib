"""Your wines and the vineyards WineLib already has outlines for (the vineyards table, from the map's vineyard sources:
Burgundy's premiers crus, Weinlagen, California's sites...): a cuvée whose name holds a vineyard of its region
("Escolle Vineyard" and Escolle, Santa Lucia Highlands; "Wehlener Sonnenuhr Spätlese" and Wehlener Sonnenuhr) is
linked to it. The French lieux-dits are matched apart (lieux_dits.py), only when no vineyard of the region is.

Settings › Maintenance › Vineyards for your wines: a preview of the matches to tick, then the ticked ones linked.
"""
from collections import defaultdict

from sqlalchemy.orm import joinedload

from lieux_dits import GENERIC, MIN_LETTERS, _matches, core, fold, same, words
from models import Vineyard, Wine

# What else a cuvée's name can say beside its vineyard, outside France: the site's kind, the grape, the style
OTHER_WORDS = {"vineyard", "vineyards", "vyd", "ranch", "estate", "block", "blocks", "old", "vine", "vines", "single",
               "reserve", "riserva", "selection", "lage", "grosses", "grosse", "gewachs", "gg", "erste", "kabinett",
               "spatlese", "auslese", "trocken", "feinherb", "halbtrocken", "alte", "reben", "riesling", "pinot",
               "noir", "gris", "chardonnay", "syrah", "shiraz", "grenache", "zinfandel", "cabernet", "sauvignon",
               "franc", "merlot", "spatburgunder", "weissburgunder", "grauburgunder", "silvaner", "gamay", "chenin",
               "viognier", "nebbiolo", "sangiovese", "barbera", "the", "of"}
NAMED = GENERIC | OTHER_WORDS
# A vineyard named only with these isn't told by a cuvée's name ("Les Blancs", "Le Village", "Les Crus": a cuvée
# "Blanc", "Clos du Village", "Grand Cru")
PLAIN = NAMED | {"village", "cote", "cotes", "coteau", "coteaux", "rose", "crus", "vigne"}


def _named(name_words):
    """Whether a name has a word of its own"""
    return any(w not in PLAIN and same(w) not in PLAIN for w in core(name_words))


def _names(v):
    """A vineyard's name as words, and without the village's adjective it may start with ("Wehlener Sonnenuhr":
    also "Sonnenuhr", which a cuvée of Wehlen may say alone)"""
    w = words(v.name)
    out = [w]
    village = words(v.village or "")
    if len(w) > 1 and village and w[0].endswith("er") and w[0][:-2] == "".join(village):
        out.append(w[1:])
    return out


def _index(session):
    """{region id: [(vineyard, [its names' words])]}: the vineyards with an outline"""
    out = defaultdict(list)
    for v in session.query(Vineyard).filter(Vineyard.boundary.isnot(None), Vineyard.region_id.isnot(None)):
        names = [n for n in _names(v) if len("".join(core(n))) >= MIN_LETTERS and _named(n)]
        if names:
            out[v.region_id].append((v, names))
    return out


def _quality(cuvee_words, names):
    """How well a cuvée names a vineyard (_matches: 2 its whole name, 1 without the articles, 0 not), by its best name;
    the full name ("Wehlener Sonnenuhr") over the short one ("Sonnenuhr")"""
    best = 0
    for i, n in enumerate(names):
        q = _matches(cuvee_words, n, core(n), NAMED)
        best = max(best, q * 2 - i if q else 0)  # 4, 3: full name; 2, 1: without the village
    return best


def candidates(session):
    """[(the cuvée's wines, [vineyard])]: the cuvées without a vineyard named after a vineyard of their region with an
    outline (the rest of the name generic), the best matches only; a village in the appellation's name ("Meursault
    Premier Cru") keeps that village's."""
    index = _index(session)
    wines = (session.query(Wine).options(joinedload(Wine.producer), joinedload(Wine.appellation))
             .filter(Wine.vineyard_id.is_(None), Wine.cuvee.isnot(None), Wine.cuvee != "").all())
    cuvees = defaultdict(list)  # a cuvée: same producer, name and appellation
    for w in wines:
        cuvees[(w.producer_id, w.cuvee.strip().lower(), w.appellation_id, w.region_id)].append(w)
    out = []
    for group in cuvees.values():
        w = group[0]
        region_id = w.region_id or (w.appellation.region_id if w.appellation else None)
        cw = words(w.cuvee)
        found = [(v, q) for v, names in index.get(region_id, []) if (q := _quality(cw, names))]
        if not found:
            continue
        best = max(q for _, q in found)
        found = [v for v, q in found if q == best]
        app = set(words(w.appellation.name)) if w.appellation else set()
        here = [v for v in found if v.village and set(words(v.village)) <= app]
        out.append((sorted(group, key=lambda x: x.vintage or ""), sorted(here or found, key=lambda v: fold(v.name))))
    return sorted(out, key=lambda x: (x[0][0].producer.name if x[0][0].producer else "", x[0][0].cuvee))


def sure(wine, options):
    """Ticked in the preview: the only vineyard it can be, in a village the wine's appellation names (Cerise, Anderson
    Valley; Chaillot, Cornas)"""
    if len(options) != 1 or not options[0].village or not wine.appellation:
        return False
    return set(words(options[0].village)) <= set(words(wine.appellation.name))


def link(wines, vineyard):
    for w in wines:
        w.vineyard_id = vineyard.id
