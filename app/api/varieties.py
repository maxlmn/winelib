"""An appellation's authorized varieties (its `varieties_text`, as the register gives it: INAO's "Cinsaut N, Sauvignon B,
Muscat À Petits Grains Roses Rs") read as grapes of the database, for the appellation's page to name and link them.
The text itself is left as published.

Each name loses INAO's colour code (B blanc, N noir, G gris, Rs rose, Rg rouge), then is found:
1. in data/reference/inao_varieties.json, the names checked by hand ("Maccabeu" is Macabeo);
2. else by a grape's name or alias, accents and case aside ("Cinsaut" is Cinsault's alias, "Meunier" Pinot Meunier's);
3. else, a colour mutation ("Grolleau Gris", "Mauzac Rose") is its grape ("Grolleau", "Mauzac");
4. else it's shown as the register names it, unlinked (a variety WineLib has no grape for)."""
import json
import os
import re
import unicodedata

from db import Varietal

HERE = os.path.dirname(os.path.abspath(__file__))
NAMES = os.path.join(HERE, "data", "reference", "inao_varieties.json")
CODE = re.compile(r"\s+(B|N|G|Gr|Rs|Rg)$")
# grey and pink berries are mutations of a grape; a "Blanc" or "Noir" is often a variety of its own (Jurançon)
MUTATION = re.compile(r"\s+(Gris|Rose|Rosé)$", re.I)
COLOURS = {"B": "white", "N": "red", "G": "grey", "Gr": "grey", "Rs": "pink", "Rg": "red"}

_names = None


def _fold(name):
    plain = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower()
    return " ".join(re.findall(r"[a-z0-9]+", plain))


def _by_hand():
    global _names
    if _names is None:
        with open(NAMES, encoding="utf-8") as f:
            _names = {_fold(k): v for k, v in json.load(f)["names"].items()}
    return _names


def index(session):
    """folded name or alias -> the grape's name (a name before an alias: no alias shadows another grape's name)"""
    rows = session.query(Varietal.name, Varietal.aliases).all()
    found = {}
    for name, _ in rows:
        found.setdefault(_fold(name), name)
    for name, aliases in rows:
        for alias in (aliases or "").split(","):
            if alias.strip():
                found.setdefault(_fold(alias), name)
    return found


def read(text, grapes):
    """[{"name": as the register names it (no colour code), "colour": "white"/"red"/... or None, "grape": the
    database's grape name or None}] for a varieties text, `grapes` from index(); codes and blanks skipped."""
    out = []
    for part in (text or "").split(","):
        raw = part.strip()
        if not raw or re.fullmatch(r"[A-Z]{2,}-[A-Z]{2}-\w+", raw):  # an id that slipped into the list (PDO-FR-A0982)
            continue
        code = CODE.search(raw)
        name = CODE.sub("", raw).strip()
        key = _fold(name)
        grape = grapes.get(_fold(_by_hand()[key])) if key in _by_hand() else grapes.get(key)
        if grape is None and MUTATION.search(name):
            grape = grapes.get(_fold(MUTATION.sub("", name)))
        out.append({"name": name, "colour": COLOURS.get(code.group(1)) if code else None, "grape": grape})
    return out
