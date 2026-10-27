"""Directories: producers and places (restaurants, homes, bars...)."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, literal_column, select, union
from sqlalchemy.orm import Session

import grape_family
from display import iso
import grapes as grape_profiles
from db import Bottle, ListItem, Place, Producer, Region, RestaurantVisit, TastingNote, Varietal, Wine, WineGrape, WineList, get_session

router = APIRouter()


@router.get("/api/grapes")
def grapes(session: Session = Depends(get_session)):
    """Every grape with its figures: the wines it's in (main grape or not), their bottles in the cellar and their
    tastings; its colour, origin and parents (VIVC), how many offspring it has."""
    wines = dict(session.query(WineGrape.varietal_id, func.count(WineGrape.wine_id)).group_by(WineGrape.varietal_id).all())
    bottles = dict(session.query(WineGrape.varietal_id, func.sum(Bottle.qty))
                   .join(Bottle, Bottle.wine_id == WineGrape.wine_id).filter(Bottle.qty > 0)
                   .group_by(WineGrape.varietal_id).all())
    tastings = dict(session.query(WineGrape.varietal_id, func.count(TastingNote.id))
                    .join(Bottle, Bottle.wine_id == WineGrape.wine_id).join(TastingNote, TastingNote.bottle_id == Bottle.id)
                    .group_by(WineGrape.varietal_id).all())
    fam = grape_family.families(session)
    rows = session.query(Varietal).order_by(Varietal.name).all()
    return [{
        "id": v.id, "name": v.name, "aliases": v.aliases, "color": v.color, "origin": v.origin,
        "parents": grape_family.parents_of(v.parents), "offspring": len(fam.offspring.get(v.id, [])),
        "parent_ids": [fam.node(p)["id"] for p in grape_family.parents_of(v.parents)],
        "wines": wines.get(v.id, 0), "bottles": int(bottles.get(v.id) or 0), "tastings": tastings.get(v.id, 0),
        "profile": grape_profiles.has_profile(v),
    } for v in rows]


@router.get("/api/producers")
def producers(session: Session = Depends(get_session)):
    tastings = dict(session.query(Wine.producer_id, func.count(TastingNote.id))
                    .join(Bottle, Bottle.wine_id == Wine.id).join(TastingNote, TastingNote.bottle_id == Bottle.id)
                    .group_by(Wine.producer_id).all())
    bottles = dict(session.query(Wine.producer_id, func.sum(Bottle.qty))
                   .join(Bottle, Bottle.wine_id == Wine.id).filter(Bottle.qty > 0)
                   .group_by(Wine.producer_id).all())
    # The lists each producer is on (itself, or one of its wines): the Lists filter, a link to each
    on_lists = {}
    for pid, lid, lname in (session.query(ListItem.producer_id, WineList.id, WineList.name)
                            .join(WineList, WineList.id == ListItem.list_id).distinct().order_by(WineList.name)):
        on_lists.setdefault(pid, []).append({"id": lid, "name": lname})
    rows = (session.query(Producer.id, Producer.name, Region.name, Region.color, Producer.subregion, Producer.village,
                          Producer.winemaker, Producer.notes)
            .outerjoin(Region, Producer.region_id == Region.id)
            .order_by(Region.name, Producer.subregion, Producer.village, Producer.name).all())
    return [
        {"id": pid, "name": name, "region": region, "color": color, "subregion": subregion, "village": village,
         "winemaker": winemaker, "lists": [x["name"] for x in on_lists.get(pid, [])], "list_refs": on_lists.get(pid, []),
         "notes": notes, "tastings": tastings.get(pid, 0), "bottles": int(bottles.get(pid) or 0)}
        for pid, name, region, color, subregion, village, winemaker, notes in rows
    ]


def coord(x):
    return round(x, 5) if x is not None else None  # ~1 m


@router.get("/api/places")
def places(session: Session = Depends(get_session)):
    """A visit is a distinct day at a place, with wine (a tasting note) or without (a restaurant visit)."""
    days = union(
        select(TastingNote.place_id, TastingNote.date).where(TastingNote.date.isnot(None)),
        select(RestaurantVisit.place_id, RestaurantVisit.date).where(RestaurantVisit.date.isnot(None)),
    ).subquery()
    visits = {pid: (n, last) for pid, n, last in session.execute(
        select(days.c.place_id, func.count(literal_column("*")), func.max(days.c.date)).group_by(days.c.place_id))}
    tastings = dict(session.query(TastingNote.place_id, func.count()).group_by(TastingNote.place_id).all())
    out = []
    for p in session.query(Place).order_by(Place.name).all():
        n, last = visits.get(p.id, (0, None))
        out.append({
            "id": p.id, "name": p.name, "city": p.city, "country": p.country, "type": p.type,
            "stars": p.michelin_stars or 0, "notes": p.notes, "lat": coord(p.lat), "lng": coord(p.lng),
            "visits": n, "last_visit": iso(last), "tastings": tastings.get(p.id, 0),
        })
    # Most recently visited first, never-visited last
    out.sort(key=lambda p: p["last_visit"] or "", reverse=True)
    return out
