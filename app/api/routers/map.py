"""Map: region outlines, then appellation and vineyard shapes for what's picked.

The map opens on one coarse outline per region (GET /api/map/overview). A region's page gets an index
(names and figures, no geometry: small, revalidated with an ETag), and the geometries of only what's
picked to draw via POST /api/map/shapes, which the browser keeps between visits.
"""
import hashlib
import json
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

import geo
from cellar import load_cellar
from db import Appellation, Bottle, Region, TastingNote, Vineyard, Wine, get_session

router = APIRouter()


def mappable_app(session=None):
    """The SQL filter for appellations with something to draw: linked to a shape in the store (
    shape_links.py sets boundary only when the store has it)."""
    return Appellation.boundary.isnot(None)


# Vineyards with something to draw, the same way
MAPPABLE_VINE = Vineyard.boundary.isnot(None)


def json_response(text):
    """Shapes come from geo already serialized: send them as they are."""
    return Response(text, media_type="application/json")


def cached_text(request: Request, text):
    """JSON text with an ETag: an unchanged response costs the browser a 304, not a download."""
    body = text.encode()
    etag = f'"{hashlib.sha1(body).hexdigest()[:20]}"'
    headers = {"ETag": etag, "Cache-Control": "no-cache"}
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=headers)
    return Response(body, media_type="application/json", headers=headers)


def cached_json(request: Request, data):
    return cached_text(request, json.dumps(data, ensure_ascii=False, separators=(",", ":")))


def map_stats(session):
    """({appellation id: figures}, {vineyard id: figures}), figures being bottles, value and tastings.
    One pass over the cellar for both."""
    apps, vines = defaultdict(lambda: {"bottles": 0, "value": 0.0}), defaultdict(lambda: {"bottles": 0, "value": 0.0})
    for b in load_cellar(session)[0]:
        for key, stats in (("appellation_id", apps), ("vineyard_id", vines)):
            if b[key]:
                stats[b[key]]["bottles"] += b["qty"]
                stats[b[key]]["value"] += b["qty"] * b["market_base"]
    rows = (session.query(Wine.appellation_id, Wine.vineyard_id, func.count(TastingNote.id))
            .select_from(TastingNote).join(Bottle, TastingNote.bottle_id == Bottle.id).join(Wine, Bottle.wine_id == Wine.id)
            .group_by(Wine.appellation_id, Wine.vineyard_id).all())
    for app_id, vine_id, n in rows:
        for k, stats in ((app_id, apps), (vine_id, vines)):
            if k:
                stats[k]["tastings"] = stats[k].get("tastings", 0) + n
    return apps, vines


def region_stats(session):
    """{region id: figures}: bottles and value from the cellar, tastings, by the wine's region."""
    stats = defaultdict(lambda: {"bottles": 0, "value": 0.0, "tastings": 0})
    ids = dict(session.query(Region.name, Region.id).all())
    for b in load_cellar(session)[0]:
        rid = ids.get(b["region"])
        if rid:
            stats[rid]["bottles"] += b["qty"]
            stats[rid]["value"] += b["qty"] * b["market_base"]
    rows = (session.query(Wine.region_id, func.count(TastingNote.id)).select_from(TastingNote)
            .join(Bottle, TastingNote.bottle_id == Bottle.id).join(Wine, Bottle.wine_id == Wine.id)
            .group_by(Wine.region_id).all())
    for rid, n in rows:
        if rid:
            stats[rid]["tastings"] += n
    return stats


def _apps(session, ids):
    return (session.query(Appellation).options(joinedload(Appellation.region_obj))
            .filter(Appellation.id.in_(ids)).order_by(Appellation.name).all()) if ids else []


def _vines(session, ids):
    return (session.query(Vineyard).options(joinedload(Vineyard.region_obj))
            .filter(Vineyard.id.in_(ids)).order_by(Vineyard.name).all()) if ids else []


def shapes_response(session, app_ids, vine_ids, region=None):
    """{"appellations": FeatureCollection, "vineyards": FeatureCollection} for some rows (detail pages);
    with `region`, also "region": a FeatureCollection holding its outline (drawn as context)."""
    app_stats, vine_stats = map_stats(session)
    a = geo.collection_json("appellation", _apps(session, app_ids), app_stats)
    v = geo.collection_json("vineyard", _vines(session, vine_ids), vine_stats)
    extra = ""
    if region is not None:
        geom, bbox = geo.region_outline(region.name)
        props = json.dumps({**_region_props(region, 0, 0, {}), "bbox": bbox}, ensure_ascii=False)
        feature = f'{{"type":"Feature","id":{region.id},"geometry":{geom},"properties":{props}}}' if geom else ""
        extra = f',"region":{{"type":"FeatureCollection","features":[{feature}]}}'
    outlines = json.dumps(geo.outlines_installed())
    return json_response(f'{{"appellations":{a},"vineyards":{v}{extra},"outlines":{outlines}}}')


def _mappable_regions(session):
    """[(region, mappable appellations, mappable vineyards)] for the regions with something to map, by name: an
    appellation or vineyard shape, or the region's own outline (Japan, China: no appellation shapes)."""
    n_apps = dict(session.query(Appellation.region_id, func.count()).filter(mappable_app(session)).group_by(Appellation.region_id).all())
    n_vines = dict(session.query(Vineyard.region_id, func.count()).filter(MAPPABLE_VINE).group_by(Vineyard.region_id).all())
    regions = [r for r in session.query(Region).order_by(Region.name).all()
               if r.id in n_apps or r.id in n_vines or geo.region_outline(r.name)[0]]
    return [(r, n_apps.get(r.id, 0), n_vines.get(r.id, 0)) for r in regions]


def _region_props(r, apps, vines, stats):
    s = stats.get(r.id, {})
    return {"id": r.id, "kind": "region", "name": r.name, "country": r.country, "color": r.color or "#9a9893",
            "appellations": apps, "vineyards": vines,
            "bottles": s.get("bottles", 0), "value": round(s.get("value", 0)), "tastings": s.get("tastings", 0)}


@router.get("/api/map/regions")
def map_regions(session: Session = Depends(get_session)):
    """Regions with something to map, with appellation / vineyard counts and your bottles and tastings."""
    stats = region_stats(session)
    return [_region_props(r, apps, vines, stats) for r, apps, vines in _mappable_regions(session)]


@router.get("/api/map/overview")
def map_overview(request: Request, session: Session = Depends(get_session)):
    """The map's first page: every region with something to map, as a coarse outline (a FeatureCollection
    with the same properties as /api/map/regions, plus each outline's bbox) and their overall extent.
    Bigger outlines come first, so smaller ones draw on top (Piemonte over Italy)."""
    stats = region_stats(session)
    features = []
    for r, apps, vines in _mappable_regions(session):
        geom, bbox = geo.region_outline(r.name)
        area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]) if bbox else 0
        props = json.dumps({**_region_props(r, apps, vines, stats), "bbox": bbox}, ensure_ascii=False)
        features.append((-area, f'{{"type":"Feature","id":{r.id},"geometry":{geom or "null"},"properties":{props}}}', bbox))
    features.sort(key=lambda f: f[0])
    extent = json.dumps(geo.merge_extents(*(b for _, _, b in features)))
    body = ",".join(f for _, f, _ in features)
    outlines = json.dumps(geo.outlines_installed())  # none: the page says where to get them
    return cached_text(request, f'{{"type":"FeatureCollection","features":[{body}],"extent":{extent},"outlines":{outlines}}}')


@router.get("/api/map/regions/{region_id}")
def map_region(region_id: int, request: Request, session: Session = Depends(get_session)):
    """A region's appellations and vineyards (for the pickers: names and figures, no geometry), its
    outline (drawn as context) and extent. Appellation and vineyard shapes come on demand, only for
    what's picked, via POST /api/map/shapes."""
    region = session.get(Region, region_id)
    if region is None:
        raise HTTPException(404, "Region not found")
    apps = (session.query(Appellation).options(joinedload(Appellation.region_obj))
            .filter(Appellation.region_id == region_id, mappable_app(session)).order_by(Appellation.name).all())
    vines = session.query(Vineyard).filter(Vineyard.region_id == region_id, MAPPABLE_VINE).all()
    app_stats, vine_stats = map_stats(session)
    outline, extent = geo.region_outline(region.name)
    return cached_json(request, {
        "version": geo.version(session),
        "region": {"id": region.id, "name": region.name, "color": region.color or "#9a9893"},
        "appellations": [geo.appellation_props(a, app_stats) for a in apps],
        "vineyards": [geo.vineyard_props(v, vine_stats) for v in vines],
        "outline": json.loads(outline) if outline else None,
        "extent": extent,
    })


class ShapeIds(BaseModel):
    appellations: list[int] = []
    vineyards: list[int] = []


@router.post("/api/map/shapes")
def map_shapes(body: ShapeIds, session: Session = Depends(get_session)):
    """Geometries only, by id: {"version", "appellations": {id: geometry | null}, "vineyards": {...}}.
    POST because a whole sub-region can be thousands of ids."""
    a = geo.geometries_json("appellation", _apps(session, body.appellations))
    v = geo.geometries_json("vineyard", _vines(session, body.vineyards))
    return json_response(f'{{"version":{json.dumps(geo.version(session))},"appellations":{a},"vineyards":{v}}}')
