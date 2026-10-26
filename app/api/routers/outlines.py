"""Outlines drawn or imported in the app, for an appellation or vineyard the shape store has none for (or a wrong
one): saved in custom_shapes, the row linked to it as boundary = 'custom:<id>', drawn like any other outline.
Deleting one puts the row's previous (official) link back."""
import json
import math
import re
import xml.etree.ElementTree as ET
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

import geo
from db import Appellation, CustomShape, Vineyard, Wine, get_session, same_cuvee

router = APIRouter()

KINDS = {"appellations": (Appellation, "appellation"), "vineyards": (Vineyard, "vineyard")}
# Like the shape store's display outlines: tolerance in degrees, coordinate decimals
DETAIL = {"appellation": (0.0005, 4), "vineyard": (0.00005, 5)}
RELATIVE_TOLERANCE = 1 / 2500


class Outline(BaseModel):
    geometry: dict  # GeoJSON: a Polygon / MultiPolygon, a Feature or a FeatureCollection of them


class NewVineyard(Outline):
    wine: int
    name: str
    village: str | None = None


class OutlineFile(BaseModel):
    filename: str
    text: str


def _row(session, kind, row_id):
    if kind not in KINDS:
        raise HTTPException(404, "Unknown kind")
    model, label = KINDS[kind]
    row = session.get(model, row_id)
    if row is None:
        raise HTTPException(404, f"{label.title()} not found")
    return row, label


def _custom_id(row):
    b = row.boundary or ""
    return int(b.split(":", 1)[1]) if b.startswith("custom:") and b.split(":", 1)[1].isdigit() else None


def to_shape(data):
    """A valid (Multi)Polygon from GeoJSON (geometry, Feature, FeatureCollection), in lon/lat; 422 otherwise."""
    import shapely
    from shapely.geometry import shape
    from shapely.ops import unary_union
    try:
        if data.get("type") == "FeatureCollection":
            parts = [shape(f["geometry"]) for f in data.get("features", []) if f.get("geometry")]
        elif data.get("type") == "Feature":
            parts = [shape(data["geometry"])]
        else:
            parts = [shape(data)]
    except (KeyError, TypeError, ValueError, AttributeError) as e:
        raise HTTPException(422, f"Not a GeoJSON shape ({e})")
    polygons = [p for p in parts if p.geom_type in ("Polygon", "MultiPolygon") and not p.is_empty]
    if not polygons:
        raise HTTPException(422, "No polygon to save: draw an outline (at least three points)")
    g = shapely.make_valid(unary_union(polygons))
    if g.geom_type == "GeometryCollection":
        g = unary_union([p for p in g.geoms if p.geom_type in ("Polygon", "MultiPolygon")])
    if g.is_empty or g.area == 0:
        raise HTTPException(422, "The outline has no area")
    w, s, e, n = g.bounds
    if not (-180 <= w <= e <= 180 and -90 <= s <= n <= 90):
        raise HTTPException(422, "Coordinates aren't longitude / latitude")
    return g


def display(g, kind):
    """(display GeoJSON, bbox) simplified like the store's, so drawn and official outlines look alike."""
    import numpy as np
    import shapely
    tolerance, digits = DETAIL[kind]
    w, s, e, n = g.bounds
    small = shapely.simplify(g, max(tolerance, math.hypot(e - w, n - s) * RELATIVE_TOLERANCE), preserve_topology=True)
    small = shapely.transform(small, lambda c: np.round(c, digits))
    return shapely.to_geojson(small), ",".join(str(round(b, 6)) for b in g.bounds)


@router.get("/api/{kind}/{row_id}/outline")
def get_outline(kind: str, row_id: int, session: Session = Depends(get_session)):
    """{"custom": the outline drawn in the app (GeoJSON, as drawn) or null, "official": the store's outline the row
    had (to start from), "boundary", "frame": where to open the map (the outline's box, else the region's)}."""
    import shapely
    row, label = _row(session, kind, row_id)
    custom = session.get(CustomShape, _custom_id(row)) if _custom_id(row) else None
    official_link = custom.replaces if custom else row.boundary
    official, frame = None, None
    if official_link and not official_link.startswith("custom:"):
        found = geo._lookup(official_link)
        if found:
            official, frame = json.loads(shapely.to_geojson(shapely.from_wkb(found[0]))), list(found[1])
    if custom:
        frame = [float(b) for b in custom.bbox.split(",")]
    if frame is None and row.region_obj is not None:
        frame = geo.region_outline(row.region_obj.name)[1]
    return {"boundary": row.boundary, "custom": json.loads(custom.geometry) if custom else None, "official": official,
            "frame": frame}


@router.get("/api/{kind}/{row_id}/outline/full")
def full_outline(kind: str, row_id: int, session: Session = Depends(get_session)):
    """{"geometry", "bbox"}: the row's outline at full detail, from the shape store (a page's "Full detail")."""
    row, label = _row(session, kind, row_id)
    found = geo.detail(row.boundary)
    if found is None:
        raise HTTPException(404, f"No detailed outline for this {label}")
    text, box = found
    return Response(f'{{"geometry":{text},"bbox":{json.dumps(box)}}}', media_type="application/json")


def _wine(session, wine_id):
    w = session.get(Wine, wine_id)
    if w is None:
        raise HTTPException(404, "Wine not found")
    return w


@router.get("/api/wines/{wine_id}/new-vineyard")
def new_vineyard_start(wine_id: int, session: Session = Depends(get_session)):
    """What the new vineyard page starts from: a name (the cuvée), the region, and where to open the map (the
    wine's appellation outline, else its region's)."""
    w = _wine(session, wine_id)
    frame = None
    if w.appellation is not None:
        found = geo._lookup(w.appellation.boundary, session)
        frame = list(found[1]) if found else None
    region = w.region_obj or (w.appellation.region_obj if w.appellation else None)
    if frame is None and region is not None:
        frame = geo.region_outline(region.name)[1]
    return {"boundary": None, "custom": None, "official": None, "frame": frame,
            "name": w.cuvee or "", "region": region.name if region else None,
            "appellation": w.appellation.name if w.appellation else None,
            "wine": {"id": w.id, "producer": w.producer.name if w.producer else "", "cuvee": w.cuvee or "",
                     "vintage": w.vintage or "NV", "vineyard_id": w.vineyard_id}}


@router.post("/api/vineyards", status_code=201)
def create_vineyard(body: NewVineyard, session: Session = Depends(get_session)):
    """A vineyard drawn from a wine's page: created with its outline, then linked to the wine and to its other
    vintages that have no vineyard (as the wine form does)."""
    w = _wine(session, body.wine)
    name = body.name.strip()
    if not name:
        raise HTTPException(422, "Give the vineyard a name")
    g = to_shape(body.geometry)
    region = w.region_obj or (w.appellation.region_obj if w.appellation else None)
    v = Vineyard(name=name, village=(body.village or "").strip() or None, region_obj=region,
                 sub_region=w.appellation.subregion if w.appellation else None)
    session.add(v)
    session.flush()
    _link(session, v, "vineyard", g)
    family = (session.query(Wine)
              .filter(Wine.producer_id == w.producer_id, same_cuvee(w.cuvee), Wine.vineyard_id.is_(None),
                      Wine.appellation_id.is_(None) if w.appellation_id is None else Wine.appellation_id == w.appellation_id,
                      Wine.varietal_id.is_(None) if w.varietal_id is None else Wine.varietal_id == w.varietal_id)
              .all())
    for x in {w, *family}:
        x.vineyard_id = v.id
    session.commit()
    geo.custom_changed(int(v.boundary.split(":")[1]))
    return {"id": v.id, "wines_linked": len({w, *family})}


def _link(session, row, label, g):
    """Saves outline g for the row (creating its custom shape, or replacing the one it has) and links the row to
    it, without committing."""
    import shapely
    shown, bbox = display(g, label)
    custom = session.get(CustomShape, _custom_id(row)) if _custom_id(row) else None
    if custom is None:
        custom = CustomShape(kind=label, replaces=row.boundary)
        session.add(custom)
    custom.name, custom.geometry, custom.display, custom.bbox = row.name, shapely.to_geojson(g), shown, bbox
    custom.updated = datetime.now()
    session.flush()
    row.boundary = f"custom:{custom.id}"
    return custom, bbox


@router.put("/api/{kind}/{row_id}/outline")
def save_outline(kind: str, row_id: int, body: Outline, session: Session = Depends(get_session)):
    """Saves the drawn outline (creating it, or replacing the one the row has) and links the row to it."""
    row, label = _row(session, kind, row_id)
    custom, bbox = _link(session, row, label, to_shape(body.geometry))
    session.commit()
    geo.custom_changed(custom.id)
    return {"boundary": row.boundary, "bbox": [float(b) for b in bbox.split(",")]}


@router.delete("/api/{kind}/{row_id}/outline")
def delete_outline(kind: str, row_id: int, session: Session = Depends(get_session)):
    """Deletes the row's drawn outline; the official link it replaced (if any) is back."""
    row, _ = _row(session, kind, row_id)
    custom = session.get(CustomShape, _custom_id(row)) if _custom_id(row) else None
    if custom is None:
        raise HTTPException(404, "No outline drawn for this one")
    row.boundary = custom.replaces
    shape_id = custom.id
    session.delete(custom)
    session.commit()
    geo.custom_changed(shape_id)
    return {"boundary": row.boundary}


def _kml_polygons(text):
    """GeoJSON Polygons from a KML file's <Polygon> elements (outer and inner rings), any namespace."""
    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        raise HTTPException(422, f"Not a KML file ({e})")
    local = lambda el: el.tag.rsplit("}", 1)[-1]  # noqa: E731

    def ring(el):
        coords = next((c.text for c in el.iter() if local(c) == "coordinates" and c.text), "")
        pts = [[float(v) for v in p.split(",")[:2]] for p in re.split(r"\s+", coords.strip()) if p]
        return pts if len(pts) >= 3 else None

    polygons = []
    for poly in (el for el in root.iter() if local(el) == "Polygon"):
        outer = [ring(b) for b in poly if local(b) == "outerBoundaryIs"]
        inner = [ring(b) for b in poly if local(b) == "innerBoundaryIs"]
        if outer and outer[0]:
            polygons.append({"type": "Polygon", "coordinates": [outer[0]] + [r for r in inner if r]})
    return polygons


@router.post("/api/outlines/parse")
def parse_file(body: OutlineFile):
    """The outline in an uploaded GeoJSON or KML file (e.g. drawn in Google Earth), to show before saving:
    {"geometry"}."""
    import shapely
    name = body.filename.lower()
    if name.endswith(".kml"):
        polygons = _kml_polygons(body.text)
        data = {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": p} for p in polygons]}
    elif name.endswith((".geojson", ".json")):
        try:
            data = json.loads(body.text)
        except ValueError as e:
            raise HTTPException(422, f"Not a GeoJSON file ({e})")
    else:
        raise HTTPException(422, "A .geojson, .json or .kml file")
    return {"geometry": json.loads(shapely.to_geojson(to_shape(data)))}
