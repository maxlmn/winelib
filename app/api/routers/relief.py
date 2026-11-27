"""A vineyard's relief (relief.py): its elevation, slope and aspect, contour lines and height bands, worked out the first
time its page asks (or by the Maintenance task) and kept in `reliefs`, keyed by its outline. An outline with nothing to
work out (too big, too small, its outline not in the store) is kept too, as a marker (`none_reason`), so it isn't
fetched again on every visit; it's tried again after RETRY_DAYS."""
import json
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from shapely.errors import ShapelyError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import geo
import relief
from db import Relief, Vineyard, get_session

router = APIRouter()
log = logging.getLogger(__name__)
RETRY_DAYS = 30
# The contours' JSON as it's written now ({"lines": [...], "bands": [...]}); a row from before (a list, or none) is
# worked out again. The one test of it, in SQL and in Python.
CONTOURS_PREFIX = '{"lines"'
HAS_CONTOURS = Relief.contours.like(CONTOURS_PREFIX + "%")


def has_contours(row):
    return (row.contours or "").startswith(CONTOURS_PREFIX)


def stale(session, row):
    """A drawn outline saved again since its relief was worked out"""
    updated = geo.custom_updated(session, row.boundary)
    return updated is not None and updated > row.computed


def current(session, row):
    """A kept row still good: worked out (or found to have nothing) since its outline last changed; a marker not too
    old"""
    if row is None or stale(session, row):
        return False
    if row.none_reason:
        return row.computed > datetime.now() - timedelta(days=RETRY_DAYS)
    return has_contours(row)


def public(row):
    if row is None or row.none_reason:
        return None
    return {"elevation": {"min": row.elevation_min, "mean": row.elevation_mean, "max": row.elevation_max},
            "slope": {"median": row.slope_median, "steep": row.slope_steep},
            "aspect": row.aspect, "facing": relief.compass(row.aspect) if row.aspect is not None else None}


def work_out(session, boundary, get=None):
    """The Relief row for an outline, worked out (and saved, not committed) if missing or no longer current; a marker
    row (none_reason) when there's nothing to work out. Raises OSError when the terrain tiles can't be reached,
    ValueError for a tile that isn't one."""
    row = session.get(Relief, boundary)
    if current(session, row):
        return row
    g = geo.outline(session, boundary)
    try:
        found = relief.compute(g, **({"get": get} if get else {})) if g is not None else None
        reason = None if found else ("no outline to work from" if g is None else "too big or too small to work out")
    except ShapelyError as e:  # an outline the geometry library can't cut: kept as such, not tried on every visit
        found, reason = None, f"its outline can't be worked with ({e.__class__.__name__})"
    row = row or Relief(boundary=boundary)
    if found:
        row.elevation_min, row.elevation_mean, row.elevation_max = (found["elevation"][k] for k in ("min", "mean", "max"))
        row.slope_median, row.slope_steep = found["slope"]["median"], found["slope"]["steep"]
        row.aspect, row.zoom = found["aspect"], found["zoom"]
        row.contours, row.none_reason = json.dumps(found["contours"]), None
    else:
        row.elevation_min = row.elevation_mean = row.elevation_max = row.slope_median = row.slope_steep = 0
        row.aspect, row.zoom, row.contours, row.none_reason = None, 0, None, reason
    row.computed = datetime.now()
    session.add(row)
    return row


def save(session, boundary, work):
    """Commits what `work()` added; when another request saved the same outline meanwhile (two first visits at once),
    theirs is kept and read back"""
    try:
        row = work()
        session.commit()
        return row
    except IntegrityError:
        session.rollback()
        return session.get(Relief, boundary)


def work_out_later(bind, boundary):
    """A vineyard's outline just saved (routers/outlines.py, run after the answer): its relief worked out on a session
    of its own, so its page and the map's contours have it at once; tiles unreachable or anything else, it's left for
    the page or the Maintenance task to try again"""
    from sqlalchemy.orm import Session as Own
    with Own(bind=bind) as session:
        try:
            save(session, boundary, lambda: work_out(session, boundary))
        except Exception as e:  # noqa: BLE001 (never the saving's error: it has answered already)
            session.rollback()
            log.warning("relief of %s, after saving it: %s", boundary, e)


@router.get("/api/vineyards/{vineyard_id}/relief")
def vineyard_relief(vineyard_id: int, session: Session = Depends(get_session)):
    """{"elevation": {"min", "mean", "max"} (m), "slope": {"median", "steep"} (degrees), "aspect" (degrees from north,
    null when flat or facing every way), "facing" ("ESE")}, or null when it has no outline or nothing to work out;
    503 when the terrain tiles can't be reached (nothing kept: asked again next time)."""
    v = session.get(Vineyard, vineyard_id)
    if v is None:
        raise HTTPException(404, "Vineyard not found")
    if not v.boundary:
        return None
    try:
        return public(save(session, v.boundary, lambda: work_out(session, v.boundary)))
    except (OSError, ValueError) as e:  # urllib's errors are OSErrors; a tile that isn't one, ValueError
        log.warning("relief of %s: %s", v.boundary, e)
        session.rollback()
        raise HTTPException(503, "The terrain tiles couldn't be reached")


@router.get("/api/map/vineyard-contours")
def vineyard_contours(ids: str = "", session: Session = Depends(get_session)):
    """The contour lines and height bands inside some vineyards' outlines (ids "1,2,3", a hundred or so at a time), as
    one GeoJSON FeatureCollection: bands ("kind": "band", "t" from 0 at the bottom to 1 at the top) then lines
    ("kind": "line"), each with its vineyard and elevation ("ele"). Only those already worked out and still current
    (a redrawn outline's are left out until worked out again): nothing is fetched here."""
    wanted = [int(i) for i in ids.split(",") if i.strip().isdigit()][:500]
    rows = (session.query(Vineyard.id, Relief).join(Relief, Relief.boundary == Vineyard.boundary)
            .filter(Vineyard.id.in_(wanted), HAS_CONTOURS).all()) if wanted else []
    features = []
    for vid, row in rows:
        if stale(session, row):
            continue
        try:
            found = json.loads(row.contours)
        except ValueError:  # one damaged row doesn't take the others' away
            log.warning("contours of %s: not JSON", row.boundary)
            continue
        features += [{"type": "Feature", "geometry": b["area"], "properties": {"vineyard": vid, "kind": "band",
                                                                              "ele": b["ele"], "t": b["t"]}}
                     for b in found.get("bands", [])]
        features += [{"type": "Feature", "geometry": c["line"], "properties": {"vineyard": vid, "kind": "line",
                                                                              "ele": c["ele"]}}
                     for c in found.get("lines", [])]
    return {"type": "FeatureCollection", "features": features}


def missing(session):
    """The vineyards your wines use that have an outline but no current relief (one per outline); those found to have
    nothing to work out are left out until RETRY_DAYS later"""
    from db import Wine
    rows = (session.query(Vineyard).join(Wine, Wine.vineyard_id == Vineyard.id)
            .filter(Vineyard.boundary.isnot(None)).distinct().order_by(Vineyard.name).all())
    kept = {r.boundary: r for r in session.query(Relief).filter(Relief.boundary.in_({v.boundary for v in rows}))}
    seen, out = set(), []
    for v in rows:
        if v.boundary in seen or current(session, kept.get(v.boundary)):
            continue
        seen.add(v.boundary)
        out.append(v)
    return out


def describe(row):
    """'ESE · 262-301 m · 5°', or why there's nothing"""
    if row.none_reason:
        return row.none_reason
    facing = (relief.compass(row.aspect) if row.aspect is not None
              else "flat" if row.slope_median < relief.FLAT_DEG else "several ways")
    return f"{facing} · {row.elevation_min:.0f}-{row.elevation_max:.0f} m · {row.slope_median:g}°"


def fill(session, todo, commit, log=print):
    """[(vineyard, Relief row or None, error or None)] for the vineyards in `todo` (from missing()); a preview fetches
    nothing"""
    out = []
    for v in todo:
        if not commit:
            out.append((v, None, None))
            continue
        try:
            row = save(session, v.boundary, lambda: work_out(session, v.boundary))
            out.append((v, row, row.none_reason if row is not None else "kept by another run"))
            if row is not None and not row.none_reason:
                log(f"{v.name}: {describe(row)}")
        except (OSError, ValueError) as e:
            session.rollback()
            out.append((v, None, f"tiles unreachable ({e})"))
        except Exception as e:  # one vineyard that can't be worked out doesn't stop the others
            session.rollback()
            out.append((v, None, f"couldn't be worked out ({type(e).__name__})"))
    return out
