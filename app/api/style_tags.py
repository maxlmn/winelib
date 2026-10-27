"""Style tags: a wine's style in a few words, set on the wine by hand or picked in its tastings, gathered when shown
(never copied: deleting a tasting drops its tags). Not the tastings' `tags` column ("Dinner, Gift, corked"): that's
the occasion or that bottle, these are the wine.

A short shared vocabulary to pick from (the filters stay consistent), plus your own words."""
from collections import defaultdict

from sqlalchemy import func

from models import Bottle, TastingNote, TastingTag, WineTag

VOCABULARY = ["fresh", "mineral", "fruity", "floral", "spicy", "savoury", "earthy", "oaky", "smoky", "tannic", "light",
              "full-bodied", "rich", "elegant", "natural", "for ageing"]


def clean(tags):
    """Tags as kept: trimmed, lower case, each once, in the order given; empty ones dropped."""
    out = []
    for t in tags or []:
        t = " ".join(str(t).split()).lower()
        if t and t not in out and len(t) <= 40:
            out.append(t)
    return out


def of_wines(session, wine_ids):
    """{wine id: [{tag, set, tastings}]}: the tags set on each wine, and those of its tastings with how many; set ones
    first, then the most tasted."""
    ids = list(set(wine_ids))
    out = defaultdict(dict)
    if not ids:
        return {}
    for wid, tag in session.query(WineTag.wine_id, WineTag.tag).filter(WineTag.wine_id.in_(ids)):
        out[wid][tag] = {"tag": tag, "set": True, "tastings": 0}
    for wid, tag, n in (session.query(Bottle.wine_id, TastingTag.tag, func.count())
                        .join(TastingNote, TastingNote.id == TastingTag.tasting_id)
                        .join(Bottle, Bottle.id == TastingNote.bottle_id)
                        .filter(Bottle.wine_id.in_(ids)).group_by(Bottle.wine_id, TastingTag.tag)):
        out[wid].setdefault(tag, {"tag": tag, "set": False, "tastings": 0})["tastings"] = n
    return {wid: sorted(tags.values(), key=lambda t: (not t["set"], -t["tastings"], t["tag"])) for wid, tags in out.items()}


def used(session):
    """Every tag in use, with how many wines carry it (set or tasted), most used first."""
    wines = defaultdict(set)
    for wid, tag in session.query(WineTag.wine_id, WineTag.tag):
        wines[tag].add(wid)
    for wid, tag in (session.query(Bottle.wine_id, TastingTag.tag).join(TastingNote, TastingNote.id == TastingTag.tasting_id)
                     .join(Bottle, Bottle.id == TastingNote.bottle_id)):
        wines[tag].add(wid)
    return sorted(({"tag": t, "wines": len(w)} for t, w in wines.items()), key=lambda x: (-x["wines"], x["tag"]))
