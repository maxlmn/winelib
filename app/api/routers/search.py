"""Global search (⌘K): producers, wines, places, appellations and vineyards by name, ignoring accents."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db import Appellation, Place, Producer, Region, Varietal, Vineyard, Wine, get_session
from textsearch import fold, search as rank

router = APIRouter()


def _join(*parts):
    return " · ".join(p for p in parts if p)


def _vintage_key(v):
    return -int(v) if (v or "").isdigit() else 0


def _region(name, country):
    """A region named with its country, as everywhere in the app: "Mosel, Germany"."""
    return f"{name}, {country}" if name and country and country != name else name


def _kinds(session):
    """Each kind of result: its rows (sorted as shown), the texts a query matches (the first ranks) and its entry."""
    regions = session.query(Region.id, Region.name, Region.country).all()
    yield "region", regions, lambda r: (r[1],), lambda r: {"title": r[1], "sub": r[2] if r[2] != r[1] else "", "region": r[1]}

    grapes = session.query(Varietal.id, Varietal.name, Varietal.aliases).all()
    yield "grape", grapes, lambda r: (r[1], r[2] or ""), lambda r: {"title": r[1], "sub": r[2] or ""}

    producers = (session.query(Producer.id, Producer.name, Region.name, Producer.village, Region.country)
                 .outerjoin(Region, Producer.region_id == Region.id).all())
    yield "producer", producers, lambda r: (r[1],), lambda r: {"title": r[1], "sub": _join(_region(r[2], r[4]), r[3]),
                                                               "region": r[2]}

    # Every word must appear in producer, cuvée, vintage or appellation: "rougeard bourg 2016", "chablis 2019"
    wines = (session.query(Wine.id, Producer.name, Wine.cuvee, Wine.vintage, Appellation.name, Region.name, Region.country)
             .join(Producer, Wine.producer_id == Producer.id)
             .outerjoin(Appellation, Wine.appellation_id == Appellation.id)
             .outerjoin(Region, Wine.region_id == Region.id).all())
    wines.sort(key=lambda r: (fold(r[1]), fold(r[2]), _vintage_key(r[3])))
    yield "wine", wines, lambda r: (r[1], r[2], r[3], r[4]), lambda r: {
        "title": " ".join(x for x in r[1:4] if x), "sub": _join(r[4], _region(r[5], r[6])), "region": r[5]}

    places = session.query(Place.id, Place.name, Place.city, Place.country, Place.michelin_stars).all()
    yield "place", places, lambda r: (r[1], r[2]), lambda r: {"title": r[1], "sub": _join(r[2], r[3], "★" * (r[4] or 0))}

    apps = (session.query(Appellation.id, Appellation.name, Region.name, Appellation.type, Region.country)
            .outerjoin(Region, Appellation.region_id == Region.id).all())
    yield "appellation", apps, lambda r: (r[1],), lambda r: {"title": r[1], "sub": _join(_region(r[2], r[4]), r[3]),
                                                               "region": r[2]}

    vines = (session.query(Vineyard.id, Vineyard.name, Vineyard.village, Region.name, Region.country)
             .outerjoin(Region, Vineyard.region_id == Region.id).all())
    yield "vineyard", vines, lambda r: (r[1], r[2]), lambda r: {"title": r[1], "sub": _join(r[2], _region(r[3], r[4])),
                                                                 "region": r[3]}


def _sorted(kind, rows):
    return rows if kind == "wine" else sorted(rows, key=lambda r: fold(r[1]))


@router.get("/api/search")
def search(q: str = "", limit: int = 6, session: Session = Depends(get_session)):
    if len(q.strip()) < 2:
        return {"results": []}
    return {"results": [{"kind": kind, "id": r[0], **entry(r)}
                        for kind, rows, fields, entry in _kinds(session)
                        for r in rank(_sorted(kind, rows), q, fields, limit)]}


@router.get("/api/search/all")
def search_all(session: Session = Depends(get_session)):
    """Everything search can find, with the texts a query matches ("fields", the first ranks): the static demo
    searches it in the browser (app/web/src/lib/demo.ts), as /api/search would."""
    return {"entries": [{"kind": kind, "id": r[0], **entry(r), "fields": [f or "" for f in fields(r)]}
                        for kind, rows, fields, entry in _kinds(session) for r in _sorted(kind, rows)]}
