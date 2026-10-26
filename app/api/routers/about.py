"""About the data (Settings › About the data): where the reference data and the map come from, their licences and
credits, how it was built (app/api/data/docs/*.md, also linked from the README), and what this database holds."""
import os

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

import grapes as grape_profiles
import map_pack
from db import Appellation, Region, Varietal, Vineyard, get_session

router = APIRouter()

DOCS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "docs")


def _doc(name):
    with open(os.path.join(DOCS, name), encoding="utf-8") as f:
        return f.read()


def _filled(column):
    return func.count().filter((column.isnot(None)) & (column != ""))


@router.get("/api/about/data")
def about_data(session: Session = Depends(get_session)):
    """{"sources", "built"}: Markdown; "counts": what this database holds; "by_country", "by_type": its appellations;
    "map_credits": the installed outlines' credits."""
    a_total, a_linked = session.query(func.count(Appellation.id), _filled(Appellation.boundary)).one()
    v_total, v_linked = session.query(func.count(Vineyard.id), _filled(Vineyard.boundary)).one()
    grapes = session.query(Varietal).all()
    with_profile = sum(1 for v in grapes if grape_profiles.has_profile(v))
    countries = (session.query(Region.country, func.count(Appellation.id))
                 .join(Appellation, Appellation.region_id == Region.id)
                 .group_by(Region.country).order_by(func.count(Appellation.id).desc()).all())
    types = (session.query(Appellation.type, func.count(Appellation.id)).filter(Appellation.type.isnot(None))
             .group_by(Appellation.type).order_by(func.count(Appellation.id).desc()).limit(12).all())
    return {
        "sources": _doc("sources.md"),
        "built": _doc("how-built.md"),
        "counts": {
            "regions": session.query(func.count(Region.id)).scalar(),
            "countries": len({c for c, _ in countries if c}),
            "appellations": a_total, "appellations_outlined": a_linked,
            "vineyards": v_total, "vineyards_outlined": v_linked,
            "grapes": len(grapes),
            "grapes_vivc": sum(1 for v in grapes if v.vivc),
            "grapes_parents": sum(1 for v in grapes if (v.parents or "").strip()),
            "grapes_profile": with_profile,
        },
        "by_country": [{"name": c or "Unknown", "count": n} for c, n in countries],
        "by_type": [{"name": t, "count": n} for t, n in types],
        "map_credits": map_pack.credits(),
    }
