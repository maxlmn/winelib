"""A vineyard's geology (geology.py): BRGM's formations from the map pack in France, worked out on each request;
Macrostrat's elsewhere, asked once and kept in `geologies`, keyed by the outline."""
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import geo
import geology
from db import CustomShape, Geology, Vineyard, get_session
from routers.relief import outline

router = APIRouter()
log = logging.getLogger(__name__)


def _stale(session, boundary, computed):
    """A drawn outline saved again since"""
    cid = geo.custom_id(boundary)
    custom = session.get(CustomShape, cid) if cid is not None else None
    return custom is not None and custom.updated > computed


def of(session, boundary):
    """{"source", "scale", "units"} for an outline, or None (no outline, or no map there). Raises OSError when
    Macrostrat is needed and can't be reached."""
    g = outline(session, boundary)
    if g is None or g.is_empty:
        return None
    units = geology.brgm(g)
    if units:
        return {"source": "brgm", "scale": "1:50,000", "units": units}
    row = session.get(Geology, boundary)
    if row is None or _stale(session, boundary, row.computed):
        p = g.representative_point()
        found = geology.macrostrat(p.y, p.x) or {}
        row = row or Geology(boundary=boundary)
        row.data, row.computed = json.dumps(found), datetime.now()
        session.add(row)
        session.commit()
    data = json.loads(row.data)
    return {"source": "macrostrat", **data} if data else None


@router.get("/api/vineyards/{vineyard_id}/geology")
def vineyard_geology(vineyard_id: int, session: Session = Depends(get_session)):
    """{"source": "brgm" / "macrostrat", "scale", "units": [{"notation", "name", "colour", "share", ("lithology",
    "age": Macrostrat's)}]} largest first, or null; 503 when Macrostrat can't be reached (nothing kept)."""
    v = session.get(Vineyard, vineyard_id)
    if v is None:
        raise HTTPException(404, "Vineyard not found")
    if not v.boundary:
        return None
    try:
        return of(session, v.boundary)
    except (OSError, ValueError) as e:
        log.warning("geology of %s: %s", v.boundary, e)
        session.rollback()
        raise HTTPException(503, "Macrostrat couldn't be reached")
