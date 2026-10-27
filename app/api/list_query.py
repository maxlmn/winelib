"""Lists made from criteria: tags, colour, region, grape, vintages, in the cellar or tasted, your rating, words in the
name. A list made once takes the matching wines as its entries; a live list keeps its criteria and shows whatever
matches today (its entries made when it's read, never stored)."""
import json
import re
import unicodedata
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

import style_tags
from cellar import grapes_by_wine
from models import Bottle, ListItem, Region, TastingNote, Wine


class Criteria(BaseModel):
    """Which of your wines (each vintage) a list takes. Every criterion given must hold; empty ones don't count."""
    tags: list[str] = Field(default_factory=list, description='style tags: "fresh", "mineral"...')
    tags_all: bool = Field(False, description="every tag (true), or any of them (false)")
    colors: list[str] = Field(default_factory=list, description="Red, White, Rose, Bubbles, Bubbles Rose, Sweet, Orange, Fortified")
    regions: list[str] = Field(default_factory=list, description='WineLib\'s regions: "Loire", "Bourgogne"...')
    grapes: list[str] = Field(default_factory=list, description="any of these grapes")
    vintage_from: int | None = None
    vintage_to: int | None = None
    where: Literal["any", "cellar", "tasted"] = Field("any", description="in the cellar now, tasted, or either")
    min_rating: int | None = Field(None, ge=50, le=100, description="your best rating for it at least this")
    text: str = Field("", description="words in the producer, cuvée or appellation")

    def empty(self):
        return self == Criteria()


def fold(s):
    return unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()


def _year(vintage):
    m = re.match(r"\d{4}", vintage or "")
    return int(m.group()) if m else None


def matching(session, c: Criteria):
    """Your wines (with a bottle: owned or drunk) meeting the criteria, by region, producer, cuvée and vintage."""
    q = session.query(Wine).options(joinedload(Wine.producer), joinedload(Wine.region_obj), joinedload(Wine.appellation))
    owned = select(Bottle.wine_id).where(Bottle.qty > 0)
    tasted = select(Bottle.wine_id).join(TastingNote, TastingNote.bottle_id == Bottle.id)
    q = q.filter(Wine.id.in_(owned if c.where == "cellar" else tasted if c.where == "tasted" else select(Bottle.wine_id)))
    if c.colors:
        q = q.filter(Wine.type.in_(c.colors))
    if c.regions:
        q = q.join(Region, Wine.region_id == Region.id).filter(func.lower(Region.name).in_([r.lower() for r in c.regions]))
    wines = q.all()
    if c.vintage_from or c.vintage_to:
        wines = [w for w in wines if (y := _year(w.vintage)) and (not c.vintage_from or y >= c.vintage_from)
                 and (not c.vintage_to or y <= c.vintage_to)]
    if c.text.strip():
        words = fold(c.text).split()
        wines = [w for w in wines if all(x in fold(" ".join(filter(None, (w.producer.name if w.producer else "", w.cuvee,
                                                                          w.appellation.name if w.appellation else ""))))
                                         for x in words)]
    if c.grapes:
        by_wine, want = grapes_by_wine(session), {fold(g) for g in c.grapes}
        wines = [w for w in wines if want & {fold(g) for g in by_wine.get(w.id, [])}]
    if c.tags:
        want = set(style_tags.clean(c.tags))
        tags = style_tags.of_wines(session, [w.id for w in wines])
        has = lambda w: {t["tag"] for t in tags.get(w.id, [])}  # noqa: E731
        wines = [w for w in wines if (want <= has(w) if c.tags_all else want & has(w))]
    if c.min_rating:
        best = dict(session.query(Bottle.wine_id, func.max(TastingNote.rating)).join(TastingNote, TastingNote.bottle_id == Bottle.id)
                    .filter(Bottle.wine_id.in_([w.id for w in wines])).group_by(Bottle.wine_id).all()) if wines else {}
        wines = [w for w in wines if (best.get(w.id) or 0) >= c.min_rating]
    region = lambda w: w.region_obj.name if w.region_obj else "~"  # noqa: E731
    return sorted(wines, key=lambda w: (region(w), fold(w.producer.name if w.producer else ""), fold(w.cuvee), w.vintage or ""))


def entries(wines):
    """A live list's entries, made when it's read (never stored): ListItems not in the session, ids negative (no
    entry to edit or remove)."""
    return [ListItem(id=-w.id, kind="wine", wine_id=w.id, wine=w, producer_id=w.producer_id, producer=w.producer,
                     note=None, position=i) for i, w in enumerate(wines)]


def describe(c: Criteria):
    """The criteria in a few words: "fresh or mineral · White · Loire · 2015–2020 · in the cellar"."""
    parts = []
    if c.tags:
        parts.append((" and " if c.tags_all else " or ").join(style_tags.clean(c.tags)))
    parts += [", ".join(c.colors), ", ".join(c.regions), ", ".join(c.grapes)]
    if c.vintage_from or c.vintage_to:
        parts.append(f"{c.vintage_from or '…'}–{c.vintage_to or '…'}")
    parts.append({"cellar": "in the cellar", "tasted": "tasted", "any": ""}[c.where])
    if c.min_rating:
        parts.append(f"rated {c.min_rating}+")
    if c.text.strip():
        parts.append(f"“{c.text.strip()}”")
    return " · ".join(p for p in parts if p) or "all your wines"


def load(text):
    return Criteria(**json.loads(text)) if text else None


def dump(c: Criteria):
    return json.dumps(c.model_dump(exclude_defaults=True), ensure_ascii=False)
