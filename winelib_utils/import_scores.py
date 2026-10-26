"""Critics' scores from a CSV you bring (an export, your own notes, any critic): one review per row, one column per
field, so nothing is guessed from a name. Run from the Maintenance card (Import critic scores), with the critic named.

Columns, recognised by their header (else picked on the card): producer, cuvée, vintage, colour, grape, appellation,
then score, note, link, date. Producer and vintage are needed, and a score or a note. An empty cuvée is the
producer's plain wine; an empty colour, grape or appellation doesn't narrow the match.

A row's producer is found by its name or an alias ("Also known as"); its appellation by name or alias, its grape
by name, its colour by the app's types (or Rouge, Blanc, Sparkling...), all exactly (case and accents aside). Its
wine is the producer's wine of that vintage with the same cuvée (as the Robert Parker import compares them) and the
row's colour, grape and appellation when it gives them. A wine you don't have is added with those details.
"""
import csv
import io
import re
from datetime import datetime

from winelib_utils.matching import DETAILS, Producers, cuvee_key, find_wine, norm, same_wine
from winelib_utils.models import Appellation, Producer, Varietal, Wine, has_score

FIELDS = ["producer", "cuvee", "vintage", "colour", "grape", "appellation", "score", "note", "link", "date"]
REQUIRED = ["producer", "vintage"]
# Headers that name a field (as norm() writes them)
HEADERS = {
    "producer": ["producer", "producteur", "domaine", "winery", "estate", "maker", "chateau", "produttore", "productor"],
    "cuvee": ["cuvee", "wine", "wine name", "name", "label", "vin", "cuvee name"],
    "vintage": ["vintage", "year", "millesime", "annee", "vintage year", "annata", "anada"],
    "colour": ["colour", "color", "type", "couleur", "wine type", "style"],
    "grape": ["grape", "grapes", "varietal", "variety", "cepage", "cepages", "grape variety", "vitigno", "uva"],
    "appellation": ["appellation", "aoc", "aop", "doc", "docg", "ava", "denomination", "designation"],
    "score": ["score", "points", "rating", "note sur 100", "pts", "punteggio", "puntos"],
    "note": ["note", "notes", "tasting note", "tasting notes", "review", "comment", "comments", "commentaire",
             "description", "text"],
    "link": ["link", "url", "review link", "review url", "lien", "source"],
    "date": ["date", "review date", "published", "tasted", "tasting date", "date tasted", "date de degustation"],
}
TYPES = ["Red", "White", "Bubbles", "Bubbles Rose", "Rose", "Sweet", "Orange", "Fortified"]
COLOURS = {norm(t): t for t in TYPES} | {
    "rouge": "Red", "rosso": "Red", "tinto": "Red", "rot": "Red",
    "blanc": "White", "bianco": "White", "blanco": "White", "branco": "White", "weiss": "White",
    "rosato": "Rose", "rosado": "Rose", "pink": "Rose",
    "sparkling": "Bubbles", "sparkling white": "Bubbles", "champagne": "Bubbles", "mousseux": "Bubbles",
    "effervescent": "Bubbles", "cremant": "Bubbles", "spumante": "Bubbles", "cava": "Bubbles", "sekt": "Bubbles",
    "sparkling rose": "Bubbles Rose", "champagne rose": "Bubbles Rose", "rose champagne": "Bubbles Rose",
    "dessert": "Sweet", "liquoreux": "Sweet", "moelleux": "Sweet", "doux": "Sweet",
    "fortified": "Fortified", "port": "Fortified", "porto": "Fortified", "sherry": "Fortified", "madeira": "Fortified",
}

ADD = "new wine"
FILL = "score for a wine you have"
REPLACE = "replaces this critic's other score"


def read(text):
    """(headers, rows) from the CSV's text: comma, semicolon or tab separated; rows as {header: value}."""
    text = text.lstrip("﻿")
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    headers = [h for h in (reader.fieldnames or []) if h and h.strip()]
    rows = [{h: (r.get(h) or "").strip() for h in headers} for r in reader]
    return headers, [r for r in rows if any(r.values())]


def columns(headers):
    """{field: header} for the headers that name a field (the first one for each)."""
    out = {}
    for h in headers:
        key = norm(h)
        field = next((f for f, names in HEADERS.items() if key in names and f not in out), None)
        if field:
            out[field] = h
    return out


def vintage_of(text):
    """"2019" (or "2019.0" from a spreadsheet), "NV" (NV, MV, empty "n.v."), or None when it's neither."""
    t = (text or "").strip()
    if m := re.fullmatch(r"(\d{4})(\.0)?", t):
        return m.group(1)
    if norm(t).replace(" ", "") in ("nv", "mv", "sa", "nonvintage"):
        return "NV"
    return None


def date_of(text):
    t = (text or "").strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y", "%Y/%m/%d", "%d %b %Y", "%d %B %Y", "%b %Y", "%B %Y", "%Y"):
        try:
            return datetime.strptime(t, fmt).date()
        except ValueError:
            pass
    return None


class Lookup:
    """The database's producers, appellations and grapes by name (and alias)."""

    def __init__(self, session):
        self.producers = Producers(session.query(Producer).all())
        self.appellations = {}
        for a in session.query(Appellation).all():
            for key in {norm(name) for name in [a.name, *re.split(r"[,;]", a.aliases or "")]} - {""}:
                self.appellations.setdefault(key, []).append(a)
        self.grapes = {norm(v.name): v for v in session.query(Varietal).all() if v.name}

    def appellation(self, name, producer):
        """The appellation of that name, or None; when several share it, the one in the producer's region."""
        found = self.appellations.get(norm(name), [])
        if len(found) > 1:
            found = [a for a in found if a.region_id == producer.region_id]
        return found[0] if len(found) == 1 else None


def plan(session, critic, rows, mapping):
    """[{"line", "row" (its fields), "outcome", "wine", "producer", "appellation", "grape"...}] for each row: outcome
    ADD / FILL / REPLACE, or why it's skipped. `mapping`: {field: header}."""
    look = Lookup(session)
    wines = {}  # producer id -> its wines
    new = {}  # (producer id, vintage, cuvée key, colour, appellation id, grape id) -> line of the row adding it
    given = set()  # wine ids a row already scores
    out = []
    for n, raw in enumerate(rows, start=2):  # line 1 is the header
        row = {f: (raw.get(mapping[f]) or "").strip() if mapping.get(f) else "" for f in FIELDS}
        item = {"line": n, "row": row, "wine": None}
        out.append(item)

        def skip(why):
            item["outcome"] = why
        vintage = vintage_of(row["vintage"])
        if not row["producer"]:
            skip("no producer")
            continue
        if vintage is None:
            skip(f"vintage not understood: {row['vintage']}" if row["vintage"] else "no vintage")
            continue
        if not (row["score"] or row["note"]):
            skip("no score or note")
            continue
        producer, several = look.producers.named(row["producer"])
        if several:
            item["fits"] = several
            skip("producer ambiguous")
            continue
        if producer is None:
            skip("producer not in the database")
            continue
        item["producer"], item["matched_by"] = producer, look.producers.how
        appellation = look.appellation(row["appellation"], producer) if row["appellation"] else None
        if row["appellation"] and appellation is None:
            skip(f"appellation not in the database: {row['appellation']}")
            continue
        grape = look.grapes.get(norm(row["grape"])) if row["grape"] else None
        if row["grape"] and grape is None:
            skip(f"grape not in the database: {row['grape']}")
            continue
        colour = COLOURS.get(norm(row["colour"])) if row["colour"] else None
        if row["colour"] and colour is None:
            skip(f"colour not understood: {row['colour']}")
            continue
        item.update(vintage=vintage, appellation=appellation, grape=grape, colour=colour)

        if producer.id not in wines:
            wines[producer.id] = session.query(Wine).filter(Wine.producer_id == producer.id).all()
        key = cuvee_key(row["cuvee"], None)
        fits = [w for w in wines[producer.id]
                if (w.vintage or "NV") == vintage and same_wine(cuvee_key(w.cuvee, None), key)
                and (appellation is None or w.appellation_id == appellation.id)
                and (grape is None or w.varietal_id == grape.id) and (colour is None or w.type == colour)]
        if len(fits) > 1:  # the one named exactly, if any
            fits = [w for w in fits if norm(w.cuvee or "") == norm(row["cuvee"])] or fits
        if len(fits) > 1:
            skip(f"several wines fit ({len(fits)}: give the colour, grape or appellation)")
            continue
        if not fits:
            twin = (producer.id, vintage, key, colour, appellation and appellation.id, grape and grape.id)
            if twin in new:
                skip(f"twice in the file (line {new[twin]})")
                continue
            new[twin] = n
            item["outcome"] = ADD
            continue
        wine = item["wine"] = fits[0]
        if wine.id in given:
            skip("twice in the file")
            continue
        given.add(wine.id)
        s = wine.score_of(critic)
        item["current"] = s.score if has_score(s) else None
        if not has_score(s):
            item["outcome"] = FILL
        elif (s.score or "").strip() == row["score"] and (not row["note"] or (s.note or "").strip() == row["note"]):
            skip("already there (same score)")
        else:
            item["outcome"] = REPLACE
    return out


def apply(session, critic, items):
    """Saves the planned rows (ADD / FILL / REPLACE): new wines, then the critic's score on each. {outcome: count}."""
    counts = {ADD: 0, FILL: 0, REPLACE: 0}
    for it in items:
        row, wine = it["row"], it["wine"]
        if it["outcome"] == ADD:
            p, a = it["producer"], it["appellation"]
            wine = Wine(producer_id=p.id, cuvee=row["cuvee"], vintage=it["vintage"], type=it["colour"],
                        appellation_id=a.id if a else None, varietal_id=it["grape"].id if it["grape"] else None,
                        region_id=(a.region_id if a else None) or p.region_id)
            session.add(wine)
        wine.set_score(critic, row["score"], row["note"], row["link"], date_of(row["date"]))
        counts[it["outcome"]] += 1
    return counts


def give_score(wine, critic, review, replace=False):
    """A review ({"score", "note", "url", "date"}) given to a wine you have: "filled" when it has no score from that
    critic, "replaced" when it has another review and `replace`, else "kept" (its own review stays, or it's this one)."""
    s = wine.score_of(critic)
    if not has_score(s):
        what = "filled"
    elif not replace or (s.url and s.url.strip() == (review.get("url") or "").strip()):
        return "kept"
    else:
        what = "replaced"
    wine.set_score(critic, **review)
    return what


def give(session, producer_id, fields, critic, review, replace=False):
    """A review given to the producer's wine described by `fields` (matching.DETAILS: as edited in a preview): that
    wine if you have it (give_score), else a new one with those details. (wine, "created" / "filled" / "replaced" /
    "kept")."""
    f = {k: fields.get(k) for k in DETAILS}
    f["cuvee"] = (f["cuvee"] or "").strip()
    wine = find_wine(session, producer_id, f)
    if wine is None:
        wine = Wine(producer_id=producer_id, **f)
        session.add(wine)
        wine.set_score(critic, **review)
        return wine, "created"
    return wine, give_score(wine, critic, review, replace)


def label(it):
    """"Le Bourg 2019" as the preview lists a row."""
    return f"{it['row']['cuvee'] or '(plain)'} {it.get('vintage') or it['row']['vintage']}".strip()

