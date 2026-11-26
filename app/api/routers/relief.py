"""A vineyard's relief (relief.py): its elevation, slope and aspect, worked out the first time its page asks (or by the
Maintenance task) and kept in `reliefs`, keyed by its outline."""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import geo
import relief
from db import CustomShape, Relief, Vineyard, get_session

router = APIRouter()
log = logging.getLogger(__name__)


def outline(session, boundary):
    """The outline behind a boundary link as a shapely geometry (the store's full detail when it has it), or None"""
    import shapely
    cid = geo.custom_id(boundary)
    if cid is not None:
        custom = session.get(CustomShape, cid)
        return shapely.from_geojson(custom.geometry) if custom else None
    found = geo.detail(boundary)
    if found is not None:
        return shapely.from_geojson(found[0])
    found = geo._lookup(boundary, session)
    return shapely.from_wkb(found[0]) if found else None


def stale(session, row):
    """A drawn outline saved again since its relief was worked out"""
    cid = geo.custom_id(row.boundary)
    custom = session.get(CustomShape, cid) if cid is not None else None
    return custom is not None and custom.updated > row.computed


def public(row):
    return {"elevation": {"min": row.elevation_min, "mean": row.elevation_mean, "max": row.elevation_max},
            "slope": {"median": row.slope_median, "steep": row.slope_steep},
            "aspect": row.aspect, "facing": relief.compass(row.aspect) if row.aspect is not None else None}


def work_out(session, boundary, get=None):
    """The Relief row for an outline, worked out (and saved, not committed) if missing or stale; None when there's no
    outline or nothing to work out (too big). Raises OSError when the terrain tiles can't be reached."""
    row = session.get(Relief, boundary)
    if row is not None and not stale(session, row):
        return row
    g = outline(session, boundary)
    if g is None or g.is_empty:
        return None
    found = relief.compute(g, **({"get": get} if get else {}))
    if found is None:
        return None
    row = row or Relief(boundary=boundary)
    row.elevation_min, row.elevation_mean, row.elevation_max = (found["elevation"][k] for k in ("min", "mean", "max"))
    row.slope_median, row.slope_steep = found["slope"]["median"], found["slope"]["steep"]
    row.aspect, row.zoom, row.computed = found["aspect"], found["zoom"], datetime.now()
    session.add(row)
    return row


@router.get("/api/vineyards/{vineyard_id}/relief")
def vineyard_relief(vineyard_id: int, session: Session = Depends(get_session)):
    """{"elevation": {"min", "mean", "max"} (m), "slope": {"median", "steep"} (degrees), "aspect" (degrees from north,
    null when flat or facing every way), "facing" ("ESE")}, or null when it has no outline; 503 when the terrain
    tiles can't be reached (nothing kept: asked again next time)."""
    v = session.get(Vineyard, vineyard_id)
    if v is None:
        raise HTTPException(404, "Vineyard not found")
    if not v.boundary:
        return None
    try:
        row = work_out(session, v.boundary)
    except (OSError, ValueError) as e:  # urllib's errors are OSErrors; a tile that isn't an image, ValueError
        log.warning("relief of %s: %s", v.boundary, e)
        session.rollback()
        raise HTTPException(503, "The terrain tiles couldn't be reached")
    session.commit()
    return public(row) if row else None


def missing(session):
    """The vineyards your wines use that have an outline but no relief yet (one per outline)"""
    from db import Wine
    rows = (session.query(Vineyard).join(Wine, Wine.vineyard_id == Vineyard.id)
            .filter(Vineyard.boundary.isnot(None)).distinct().order_by(Vineyard.name).all())
    done = {b for (b,) in session.query(Relief.boundary)}
    seen, out = set(), []
    for v in rows:
        if v.boundary not in done and v.boundary not in seen:
            seen.add(v.boundary)
            out.append(v)
    return out


def describe(row):
    """'ESE · 262-301 m · 5°'"""
    facing = relief.compass(row.aspect) if row.aspect is not None else "flat"
    return f"{facing} · {row.elevation_min:.0f}-{row.elevation_max:.0f} m · {row.slope_median:g}°"


def fill(session, limit, commit, log=print):
    """[(vineyard, Relief row or None, error or None)] for up to `limit` vineyards missing one; a preview fetches
    nothing"""
    out = []
    for v in missing(session)[:limit]:
        if not commit:
            out.append((v, None, None))
            continue
        try:
            row = work_out(session, v.boundary)
            session.commit()
            out.append((v, row, None if row else "no outline to work from"))
            if row:
                log(f"{v.name}: {describe(row)}")
        except (OSError, ValueError) as e:
            session.rollback()
            out.append((v, None, f"tiles unreachable ({e})"))
    return out
