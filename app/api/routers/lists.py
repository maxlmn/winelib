"""Lists of wines to find and taste: their entries (wines, cuvées any vintage, producers; mixed), each ticked when
tasted (that vintage, any vintage of the cuvée, any wine of the producer) and with the bottles owned, worked out from
the tastings and the cellar, never stored. Also which lists a wine or a producer is on (its pages)."""
from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from db import Bottle, ListItem, Producer, TastingNote, Wine, WineList, get_session
from display import iso, vintage_label

router = APIRouter()
KINDS = ("wine", "cuvee", "producer")


class ListIn(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    source: str | None = None
    url: str | None = None


class ItemIn(BaseModel):
    kind: str
    wine_id: int | None = None
    producer_id: int | None = None
    note: str | None = None


class ItemEdit(BaseModel):
    note: str | None = None
    position: int | None = None


def family(w):
    """A cuvée's key: the same producer, cuvée name, appellation and grape (its vintages, as on the wine page)."""
    return (w.producer_id, w.cuvee or "", w.appellation_id, w.varietal_id)


class Facts:
    """What the tastings and the cellar say about some producers' wines: per wine its tastings (count, last date,
    best rating) and the bottles owned; wines grouped by cuvée and by producer."""

    def __init__(self, session, producer_ids):
        ids = set(producer_ids)
        wines = (session.query(Wine.id, Wine.producer_id, Wine.cuvee, Wine.appellation_id, Wine.varietal_id)
                 .filter(Wine.producer_id.in_(ids)).all()) if ids else []
        self.wine = {w.id: w for w in wines}
        self.by_family, self.by_producer = defaultdict(list), defaultdict(list)
        for w in wines:
            self.by_family[family(w)].append(w.id)
            self.by_producer[w.producer_id].append(w.id)
        wids = list(self.wine)
        self.tasted = {}
        self.owned = defaultdict(int)
        if wids:
            for wid, n, last, best in (session.query(Bottle.wine_id, func.count(TastingNote.id), func.max(TastingNote.date),
                                                     func.max(TastingNote.rating))
                                       .join(TastingNote, TastingNote.bottle_id == Bottle.id)
                                       .filter(Bottle.wine_id.in_(wids)).group_by(Bottle.wine_id)):
                self.tasted[wid] = (n, last, best)
            for wid, qty in (session.query(Bottle.wine_id, func.sum(Bottle.qty)).filter(Bottle.wine_id.in_(wids), Bottle.qty > 0)
                             .group_by(Bottle.wine_id)):
                self.owned[wid] = int(qty or 0)

    def wines_of(self, item):
        """The wines that count for an entry: that one, its cuvée's vintages, or its producer's wines."""
        if item.kind == "producer":
            return self.by_producer.get(item.producer_id, [])
        w = self.wine.get(item.wine_id) or item.wine
        if w is None:
            return []
        return [w.id] if item.kind == "wine" else self.by_family.get(family(w), [w.id])

    def status(self, item):
        wids = self.wines_of(item)
        tastings = [(wid, *self.tasted[wid]) for wid in wids if wid in self.tasted]
        last = max(tastings, key=lambda t: t[2] or date.min, default=None)
        return {
            "tasted": bool(tastings),
            "tastings": sum(t[1] for t in tastings),
            "last_tasted": iso(last[2]) if last else None,
            # the vintage tasted last, for a cuvée or a producer ("the 2016")
            "tasted_wine_id": last[0] if last else None,
            "best_rating": max((t[3] for t in tastings if t[3]), default=None),
            "owned": sum(self.owned.get(wid, 0) for wid in wids),
        }


def _region(item):
    w, p = item.wine, item.producer
    return (w.region_obj if w and w.region_obj else None) or (p.region_obj if p else None)


def _label(item):
    """An entry in a few words: "Producer Cuvée 2016", "Producer Cuvée (any vintage)", "Producer (any of its wines)" """
    w, p = item.wine, item.producer
    name = p.name if p else ""
    if item.kind == "producer" or w is None:
        return f"{name} (any of its wines)"
    words = " ".join(x for x in (name, w.cuvee or (w.appellation.name if w.appellation else ""),
                                 vintage_label(w.vintage, w.disgorgement_date) if item.kind == "wine" else "") if x)
    return words + (" (any vintage)" if item.kind == "cuvee" else "")


def item_json(item, facts):
    w, p = item.wine, item.producer
    region = _region(item)
    return {
        "id": item.id, "kind": item.kind, "note": item.note, "position": item.position,
        "producer": {"id": p.id, "name": p.name} if p else None,
        "wine": {"id": w.id, "cuvee": w.cuvee or "", "vintage": vintage_label(w.vintage, w.disgorgement_date),
                 "color": w.type, "appellation": w.appellation.name if w.appellation else None} if w and item.kind != "producer" else None,
        "region": region.name if region else None,
        # the wines that count for it (that one, its cuvée's vintages, its producer's): the wine list prints your
        # bottles of them
        "wine_ids": facts.wines_of(item),
        **facts.status(item),
    }


def summary(lst, facts):
    statuses = [facts.status(i) for i in lst.items]
    tasted = sum(s["tasted"] for s in statuses)
    return {"id": lst.id, "name": lst.name, "description": lst.description, "source": lst.source, "url": lst.url,
            "is_wishlist": bool(lst.is_wishlist),
            "entries": len(statuses), "tasted": tasted, "owned": sum(1 for s in statuses if s["owned"]),
            "kinds": sorted({i.kind for i in lst.items})}


def _lists(session, *filters):
    items = joinedload(WineList.items)
    q = session.query(WineList).options(items.joinedload(ListItem.wine).joinedload(Wine.region_obj),
                                        items.joinedload(ListItem.wine).joinedload(Wine.appellation),
                                        items.joinedload(ListItem.producer).joinedload(Producer.region_obj))
    return q.filter(*filters).order_by(WineList.name).all()


def _get(session, list_id):
    found = _lists(session, WineList.id == list_id)
    if not found:
        raise HTTPException(404, "List not found")
    return found[0]


def _facts_for(session, lists):
    return Facts(session, {i.producer_id for lst in lists for i in lst.items})


@router.get("/api/lists")
def lists(session: Session = Depends(get_session)):
    """Every list with its progress, and each entry's tick for the row of bottle ends."""
    found = _lists(session)
    facts = _facts_for(session, found)
    out = []
    for lst in found:
        row = summary(lst, facts)
        row["dots"] = []
        for i in lst.items:
            st, region = facts.status(i), _region(i)
            row["dots"].append({"tasted": st["tasted"], "owned": bool(st["owned"]), "region": region.name if region else None,
                                "color": i.wine.type if i.wine and i.kind != "producer" else None, "note": i.note,
                                "label": _label(i)})
        out.append(row)
    return out


@router.get("/api/lists/in-cellar")
def in_cellar(session: Session = Depends(get_session)):
    """What the lists ask you to taste that's already in the cellar: per wine owned, the lists naming it (that
    vintage, its cuvée, or its producer) whose entry isn't ticked yet. "What should I open?" suggests them first."""
    found = _lists(session)
    facts = _facts_for(session, found)
    out = defaultdict(list)
    for lst in found:
        for i in lst.items:
            if facts.status(i)["tasted"]:
                continue
            for wid in facts.wines_of(i):
                if facts.owned.get(wid) and not any(x["list_id"] == lst.id for x in out[wid]):
                    out[wid].append({"list_id": lst.id, "list": lst.name, "note": i.note, "as": i.kind})
    return dict(out)


@router.post("/api/lists/wishlist")
def wishlist(session: Session = Depends(get_session)):
    """The wishlist's id (the wine page's Wishlist button adds to it): made on first use, named Wishlist."""
    lst = session.query(WineList).filter(WineList.is_wishlist.is_(True)).first()
    if lst is None:
        lst = session.query(WineList).filter(func.lower(WineList.name) == "wishlist").first()             or WineList(name="Wishlist", description="Wines you’d like", created=date.today())
        lst.is_wishlist = True
        session.add(lst)
        session.commit()
    return {"id": lst.id}


@router.get("/api/lists/{list_id}")
def list_detail(list_id: int, session: Session = Depends(get_session)):
    lst = _get(session, list_id)
    facts = _facts_for(session, [lst])
    return {**summary(lst, facts), "items": [item_json(i, facts) for i in lst.items]}


def _fill(lst, data: ListIn):
    lst.name = data.name.strip()
    lst.description = (data.description or "").strip() or None
    lst.source = (data.source or "").strip() or None
    lst.url = (data.url or "").strip() or None


@router.post("/api/lists")
def create(data: ListIn, session: Session = Depends(get_session)):
    if session.query(WineList).filter(func.lower(WineList.name) == data.name.strip().lower()).first():
        raise HTTPException(409, f"There's already a list named “{data.name.strip()}”")
    lst = WineList(created=date.today())
    _fill(lst, data)
    session.add(lst)
    session.commit()
    return {"id": lst.id}


@router.put("/api/lists/{list_id}")
def edit(list_id: int, data: ListIn, session: Session = Depends(get_session)):
    lst = _get(session, list_id)
    other = session.query(WineList).filter(func.lower(WineList.name) == data.name.strip().lower(), WineList.id != lst.id).first()
    if other:
        raise HTTPException(409, f"There's already a list named “{data.name.strip()}”")
    _fill(lst, data)
    session.commit()
    return {"id": lst.id}


@router.delete("/api/lists/{list_id}")
def remove(list_id: int, session: Session = Depends(get_session)):
    session.delete(_get(session, list_id))
    session.commit()
    return {"deleted": list_id}


@router.post("/api/lists/{list_id}/items")
def add_item(list_id: int, data: ItemIn, session: Session = Depends(get_session)):
    """Adds a wine (that vintage), a cuvée (any vintage of the wine's) or a producer; one already there is kept."""
    lst = _get(session, list_id)
    if data.kind not in KINDS:
        raise HTTPException(422, f"An entry is one of {', '.join(KINDS)}")
    if data.kind == "producer":
        p = session.get(Producer, data.producer_id) if data.producer_id else None
        if p is None:
            raise HTTPException(404, "Producer not found")
        wine_id, producer_id = None, p.id
        same = [i for i in lst.items if i.kind == "producer" and i.producer_id == p.id]
    else:
        w = session.get(Wine, data.wine_id) if data.wine_id else None
        if w is None:
            raise HTTPException(404, "Wine not found")
        wine_id, producer_id = w.id, w.producer_id
        same = [i for i in lst.items if i.kind == data.kind and i.wine_id is not None
                and (i.wine_id == w.id if data.kind == "wine" else family(i.wine) == family(w))]
    if same:
        return {"id": same[0].id, "existing": True}
    item = ListItem(list=lst, kind=data.kind, wine_id=wine_id, producer_id=producer_id,
                    note=(data.note or "").strip() or None, position=max((i.position for i in lst.items), default=0) + 1)
    session.add(item)
    session.commit()
    return {"id": item.id, "existing": False}


def _item(session, list_id, item_id):
    item = session.get(ListItem, item_id)
    if item is None or item.list_id != list_id:
        raise HTTPException(404, "Not on this list")
    return item


@router.put("/api/lists/{list_id}/items/{item_id}")
def edit_item(list_id: int, item_id: int, data: ItemEdit, session: Session = Depends(get_session)):
    item = _item(session, list_id, item_id)
    if data.note is not None:
        item.note = data.note.strip() or None
    if data.position is not None:
        item.position = data.position
    session.commit()
    return {"id": item.id}


@router.delete("/api/lists/{list_id}/items/{item_id}")
def remove_item(list_id: int, item_id: int, session: Session = Depends(get_session)):
    session.delete(_item(session, list_id, item_id))
    session.commit()
    return {"deleted": item_id}


def memberships(session, wine=None, producer=None):
    """The lists a wine is on (as that wine, its cuvée, or through its producer) or a producer is on (itself or one
    of its wines): [{list's summary, "as": entry kind, "item": its status}]."""
    pid = wine.producer_id if wine is not None else producer.id
    items = (session.query(ListItem).options(joinedload(ListItem.wine)).filter(ListItem.producer_id == pid).all())
    if wine is not None:
        items = [i for i in items if i.kind == "producer" or (i.wine is not None and (
            i.wine_id == wine.id if i.kind == "wine" else family(i.wine) == family(wine)))]
    if not items:
        return []
    found = {lst.id: lst for lst in _lists(session, WineList.id.in_({i.list_id for i in items}))}
    facts = _facts_for(session, found.values())
    out = []
    for i in sorted(items, key=lambda i: found[i.list_id].name):
        out.append({**summary(found[i.list_id], facts), "as": i.kind, "item": {"id": i.id, "note": i.note, **facts.status(i)},
                    "wine": {"cuvee": i.wine.cuvee or "", "vintage": i.wine.vintage} if i.wine and i.kind != "producer" else None})
    return out


@router.get("/api/lists-of")
def lists_of(wine_id: int | None = None, producer_id: int | None = None, session: Session = Depends(get_session)):
    """The lists a wine or a producer is on (their pages)."""
    if wine_id:
        w = session.get(Wine, wine_id)
        if w is None:
            raise HTTPException(404, "Wine not found")
        return memberships(session, wine=w)
    p = session.get(Producer, producer_id) if producer_id else None
    if p is None:
        raise HTTPException(404, "Producer not found")
    return memberships(session, producer=p)


def marks(session, wines):
    """The lists naming these wines, for the marks beside each vintage: ({wine id: [list names]} for an entry of
    that vintage, {cuvée key: [list names]} for an entry of the cuvée, any vintage). Producer entries aren't marks
    (the Lists card shows them)."""
    pids = {w.producer_id for w in wines}
    if not pids:
        return {}, {}
    items = (session.query(ListItem).options(joinedload(ListItem.wine), joinedload(ListItem.list))
             .filter(ListItem.producer_id.in_(pids), ListItem.kind.in_(("wine", "cuvee"))).all())
    by_wine, by_family = defaultdict(list), defaultdict(list)
    for i in items:
        if i.wine is None:
            continue
        target = by_wine[i.wine_id] if i.kind == "wine" else by_family[family(i.wine)]
        if i.list.name not in target:
            target.append(i.list.name)
    return dict(by_wine), dict(by_family)
