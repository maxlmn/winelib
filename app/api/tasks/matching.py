"""Matching names to the database: producers (by name, alias or distinctive words), cuvées, wines. Shared by the
imports (import_scores.py, and the Robert Parker plug-in's name-guessing import) and the merges."""
import re
from collections import defaultdict

from unidecode import unidecode

from tasks.match_lwin import PRODUCER_PREFIXES, producer_keys
from models import Wine


# Words that name a style or a classification, not which wine it is (compared without them)
GENERIC = {"domaine", "dom", "chateau", "maison", "et", "and", "the", "de", "du", "des", "d", "la", "le", "les", "l",
           "di", "del", "della", "y", "en", "a", "s", "vin", "wine", "cuvee", "rouge", "blanc", "red", "white"}
# (the colour is compared apart: a wine of another colour isn't the same one, "Juveniles" / "Juveniles Blanc")


def norm(text):
    """Accents, case and punctuation aside; "premier" written "1er" as Robert Parker and the auction houses do
    ("premier cru", "Premier Grand Cru Classé")."""
    t = re.sub(r"[^a-z0-9]+", " ", unidecode(str(text or "")).lower()).strip()
    return re.sub(r"\bpremiers?\b", "1er", t)


# Words of producer names that don't say which producer it is ("Abreu Vineyard" is Abreu, "E. Guigal" Guigal)
PRODUCER_WORDS = set(PRODUCER_PREFIXES) | GENERIC | {
    "vineyard", "vineyards", "cellars", "cellar", "estate", "estates", "winery", "wineries", "wines", "family",
    "vignobles", "vins", "bodega", "bodegas", "dominio", "tenuta", "azienda", "agricola", "cantina", "cantine",
    "weingut", "domaines", "chateaux", "pere", "fils", "freres", "compagnie", "cie", "co", "sa", "srl", "inc", "ltd",
    "familia", "comm", "marchesi", "fattoria"}


# Words of many wines' names: a producer named by these alone needs its whole name ("Domaine de la Côte" isn't every
# Côte-Rôtie, "Domaine des Clos" every Clos)
PLACE_WORDS = {"cote", "cotes", "clos", "hill", "hills", "valley", "mont", "monte", "vigne", "vigna"}


def distinctive(name):
    """A producer name's words that tell it apart: no "Domaine", "Vineyard", initials ("E.", "JL"); all its words
    when that leaves none ("Domaine A")."""
    toks = norm(name).split()
    own = {t for t in toks if t not in PRODUCER_WORDS and len(t) > 2}
    return own if own - PLACE_WORDS else set(toks)


class Producers:
    """The database's producers by their name keys (producer_keys: with and without "Domaine", "Château de"...) and
    their distinctive words."""

    def __init__(self, producers):
        self.by_key = defaultdict(set)
        self.by_name = {}
        self.words = {}
        for p in producers:
            for k in [p.name, *producer_keys(p.name)]:  # its name as norm() writes it too ("l ecu", not "lecu")
                self.by_key[norm(k)].add(p)
            self.by_name[norm(p.name)] = p
            self.words[p.id] = (p, distinctive(p.name))
        # Other names they go by ("Also known as" on the producer form): "chave" -> Jean-Louis Chave
        self.aliases = sorted(((a.split(), p) for p in producers for a in map(norm, re.split(r"[,;]", p.aliases or ""))
                               if a), key=lambda ap: -len(ap[0]))
        self.keys = sorted(self.by_key, key=lambda k: -len(k.split()))
        self.how = ""  # how the last producer was found, for the report

    def _alias(self, tokens):
        bare = list(tokens)
        while bare and bare[0] in PRODUCER_PREFIXES:  # "Domaine Jean-Marie Fourrier": "jean marie fourrier"
            bare.pop(0)
        for at, producer in self.aliases:  # the longest alias first ("jl chave" before "chave")
            if at in (tokens[:len(at)], bare[:len(at)]):
                return producer
        return None

    def _by_words(self, tokens, within=6, start=3):
        """(producer or None, [names] when several fit): the producers whose distinctive words are all among the
        first `within` tokens, beginning by the `start`th; the one with the most such words."""
        head = tokens[:within]
        sig = [t for t in head if len(t) > 1]  # positions without initials ("Comm. G.B. Burlotto": Burlotto 2nd)
        fits = []
        for p, words in self.words.values():
            if words <= set(sig) and min(sig.index(w) for w in words) < start:
                # the one whose name comes first ("Guigal Côte-Rôtie": Guigal, not Domaine de la Côte), then the
                # most specific ("Louis Latour Corton": Louis Latour, not Château Latour)
                fits.append(((-min(sig.index(w) for w in words), len(words)), p))
        if not fits:
            return None, []
        best = max(score for score, _ in fits)
        top = [p for score, p in fits if score == best]
        return (top[0], []) if len(top) == 1 else (None, sorted(p.name for p in top))

    def exact(self, name):
        """The producer of that name (or one of its name keys), only if exactly one."""
        for k in [name, *producer_keys(name)]:
            hits = self.by_key.get(norm(k), set())
            if len(hits) == 1:
                return next(iter(hits))
        return None

    def named(self, name):
        """(producer or None, [names] when several fit) for the CSV's Producer column: its name, else its
        distinctive words."""
        self.how = "Producer column: name"
        for k in producer_keys(name):
            hits = self.by_key.get(norm(k), set())
            if len(hits) == 1:
                return next(iter(hits)), []
        toks = norm(name).split()
        alias = self._alias(toks)
        self.how = "Producer column: alias"
        if alias:
            return alias, []
        self.how = "Producer column: distinctive words"
        return self._by_words(toks, within=len(toks) + 1, start=len(toks) + 1)

    def starting(self, tokens):
        """(producer or None, [names] when several fit) for a review's name (files without a Producer column):
        the longest name key it starts with (two words or six letters at least: no "Clos" for "Clos Rougeard"),
        else an alias, else the producer whose distinctive words open it ("Guigal Côte-Rôtie": E. Guigal)."""
        self.how = "review name: starts with the name"
        for k in self.keys:
            kt = k.split()
            if (len(kt) >= 2 or len(k) >= 6) and tokens[:len(kt)] == kt:
                hits = self.by_key[k]
                if len(hits) == 1:
                    return next(iter(hits)), []
        alias = self._alias(tokens)
        self.how = "review name: alias"
        if alias:
            return alias, []
        self.how = "review name: distinctive words"
        return self._by_words(tokens)


ROSE = re.compile(r"\bros(e|ato|ado)\b")


def is_rose(text):
    """A rosé by its name: "Brut Rosé", "Rosato" (not "Clos des Roses")."""
    return bool(ROSE.search(norm(text)))


def cuvee_key(cuvee, appellation):
    """What two names of the same wine share: the cuvée's and appellation's words, generic ones aside."""
    return frozenset(t for t in norm(f"{cuvee or ''} {appellation.name if appellation else ''}").split()
                     if t not in GENERIC and t not in PRODUCER_PREFIXES)


def same_wine(a, b):
    """Three words in four in common ("Reserve Bin 94A Chardonnay" / "Reserve Bin A Chardonnay"), not fewer
    ("Art Series Sauvignon Blanc Semillon" isn't "Art Series Cabernet Sauvignon")."""
    if a == b:
        return True
    if not a or not b:
        return False
    return len(a & b) / len(a | b) >= 0.75


DETAILS = ("cuvee", "vintage", "type", "appellation_id", "varietal_id", "region_id", "lwin", "vineyard_id", "blend")


def find_wine(session, producer_id, fields):
    """The producer's wine with these details (same cuvée, vintage, appellation, grape and colour), or None."""
    from sqlalchemy import func
    same = lambda col, v: col.is_(None) if v is None else col == v  # noqa: E731
    return (session.query(Wine)
            .filter(Wine.producer_id == producer_id, func.coalesce(Wine.cuvee, "") == (fields.get("cuvee") or "").strip(),
                    same(Wine.appellation_id, fields.get("appellation_id")), same(Wine.varietal_id, fields.get("varietal_id")),
                    same(Wine.type, fields.get("type")), same(Wine.vintage, fields.get("vintage")))
            .order_by(Wine.id).first())
