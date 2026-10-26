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


@router.get("/api/search")
def search(q: str = "", limit: int = 6, session: Session = Depends(get_session)):
    if len(q.strip()) < 2:
        return {"results": []}
    results = []

    regions = session.query(Region.id, Region.name, Region.country).all()
    regions.sort(key=lambda r: fold(r[1]))
    results += [{"kind": "region", "id": r[0], "title": r[1], "sub": r[2] if r[2] != r[1] else "",
                 "region": r[1]}
                for r in rank(regions, q, lambda r: (r[1],), limit)]

    grapes = session.query(Varietal.id, Varietal.name, Varietal.aliases).all()
    grapes.sort(key=lambda r: fold(r[1]))
    results += [{"kind": "grape", "id": r[0], "title": r[1], "sub": r[2] or ""}
                for r in rank(grapes, q, lambda r: (r[1], r[2] or ""), limit)]

    producers = (session.query(Producer.id, Producer.name, Region.name, Producer.village, Region.country)
                 .outerjoin(Region, Producer.region_id == Region.id).all())
    producers.sort(key=lambda r: fold(r[1]))
    results += [{"kind": "producer", "id": r[0], "title": r[1], "sub": _join(_region(r[2], r[4]), r[3]),
                 "region": r[2]}
                for r in rank(producers, q, lambda r: (r[1],), limit)]

    # Every word must appear in producer, cuvée, vintage or appellation: "rougeard bourg 2016", "chablis 2019"
    wines = (session.query(Wine.id, Producer.name, Wine.cuvee, Wine.vintage, Appellation.name, Region.name, Region.country)
             .join(Producer, Wine.producer_id == Producer.id)
             .outerjoin(Appellation, Wine.appellation_id == Appellation.id)
             .outerjoin(Region, Wine.region_id == Region.id).all())
    wines.sort(key=lambda r: (fold(r[1]), fold(r[2]), _vintage_key(r[3])))
    results += [{"kind": "wine", "id": r[0], "title": " ".join(x for x in r[1:4] if x), "sub": _join(r[4], _region(r[5], r[6])),
                 "region": r[5]}
                for r in rank(wines, q, lambda r: (r[1], r[2], r[3], r[4]), limit)]

    places = session.query(Place.id, Place.name, Place.city, Place.country, Place.michelin_stars).all()
    places.sort(key=lambda r: fold(r[1]))
    results += [{"kind": "place", "id": r[0], "title": r[1], "sub": _join(r[2], r[3], "★" * (r[4] or 0))}
                for r in rank(places, q, lambda r: (r[1], r[2]), limit)]

    apps = (session.query(Appellation.id, Appellation.name, Region.name, Appellation.type, Region.country)
            .outerjoin(Region, Appellation.region_id == Region.id).all())
    apps.sort(key=lambda r: fold(r[1]))
    results += [{"kind": "appellation", "id": r[0], "title": r[1], "sub": _join(_region(r[2], r[4]), r[3]),
                 "region": r[2]}
                for r in rank(apps, q, lambda r: (r[1],), limit)]

    vines = (session.query(Vineyard.id, Vineyard.name, Vineyard.village, Region.name, Region.country)
             .outerjoin(Region, Vineyard.region_id == Region.id).all())
    vines.sort(key=lambda r: fold(r[1]))
    results += [{"kind": "vineyard", "id": r[0], "title": r[1], "sub": _join(r[2], _region(r[3], r[4])),
                 "region": r[3]}
                for r in rank(vines, q, lambda r: (r[1], r[2]), limit)]

    return {"results": results}
