"""Tasting notes: the journal (every tasting with its wine and place, restaurant visits, photos) and one note's details."""
import json
import os
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from sqlalchemy import text
from sqlalchemy.orm import Session, joinedload

from cellar import grapes_by_wine, to_base
from display import iso, vineyard_label, vintage_label
from db import Bottle, Place, RestaurantVisit, TastingNote, Wine, get_session, same_cuvee
import photos
import scores
from photos import photo_index, photo_url


router = APIRouter()

TASTINGS_SQL = text("""
    SELECT t.id, t.date, t.sequence AS seq, t.glasses, t.rating, t.notes, t.place_id,
           COALESCE(pl.name, t.location) AS location,
           b.id AS bottle_id, b.bottle_size AS format,
           w.id AS wine_id, w.type AS color, w.cuvee, w.vintage, w.disgorgement_date, pc.score AS score,
           p.id AS producer_id, p.name AS producer,
           r.name AS region, a.id AS appellation_id, a.name AS appellation, v.name AS varietal
    FROM tasting_notes t
    JOIN cellar b ON t.bottle_id = b.id
    JOIN wines w ON b.wine_id = w.id
    JOIN producers p ON w.producer_id = p.id
    LEFT JOIN regions r ON w.region_id = r.id
    LEFT JOIN appellations a ON w.appellation_id = a.id
    LEFT JOIN varietals v ON w.varietal_id = v.id
    LEFT JOIN places pl ON t.place_id = pl.id
    LEFT JOIN critic_scores pc ON pc.wine_id = w.id AND LOWER(pc.critic) = LOWER(:critic)
    ORDER BY t.date DESC, t.sequence
""")


def place_dict(p: Place):
    return {"id": p.id, "name": p.name, "city": p.city, "country": p.country, "type": p.type,
            "stars": p.michelin_stars or 0, "lat": p.lat, "lng": p.lng}


@router.get("/api/tastings")
def tastings(session: Session = Depends(get_session)):
    """Every tasting (newest first) with its wine, plus restaurant visits and the places both refer to."""
    rows = []
    found = session.execute(TASTINGS_SQL, {"critic": scores.preferred()}).mappings().all()
    labels = scores.labels(session, [r["wine_id"] for r in found])
    grapes = grapes_by_wine(session)
    for r in found:
        rows.append({
            "id": r["id"], "date": iso(r["date"]), "seq": r["seq"], "glasses": r["glasses"], "rating": r["rating"],
            "notes": (r["notes"] or "").strip(), "place_id": r["place_id"], "location": r["location"] or "Unknown",
            "bottle_id": r["bottle_id"], "format": r["format"], "wine_id": r["wine_id"], "color": r["color"],
            "producer_id": r["producer_id"], "producer": r["producer"], "cuvee": r["cuvee"] or "",
            "appellation_id": r["appellation_id"], "appellation": r["appellation"], "varietal": r["varietal"],
            "grapes": grapes.get(r["wine_id"]) or ([r["varietal"]] if r["varietal"] else []),
            "region": r["region"] or "Unknown", "vintage": vintage_label(r["vintage"], r["disgorgement_date"]),
            "score": r["score"] if scores.real(r["score"]) else None, "scores": labels.get(r["wine_id"]),
        })
    visits = session.query(RestaurantVisit).filter(RestaurantVisit.place_id.isnot(None)).order_by(RestaurantVisit.date.desc()).all()
    place_ids = {r["place_id"] for r in rows if r["place_id"]} | {v.place_id for v in visits}
    places = session.query(Place).filter(Place.id.in_(place_ids)).all() if place_ids else []
    body = {
        "tastings": rows,
        "visits": [{"id": v.id, "date": iso(v.date), "place_id": v.place_id, "notes": (v.notes or "").strip()} for v in visits],
        "places": {p.id: place_dict(p) for p in places},
        "photos": {stem: photos.url_for(name) for stem, name in photo_index().items()},
    }
    # Thousands of rows of plain values: written straight to JSON. FastAPI's generic encoder walks every value
    # and was most of this page's wait (default=str: a Decimal or date a database may hand back)
    return Response(json.dumps(body, ensure_ascii=False, separators=(",", ":"), default=str), media_type="application/json")


@router.get("/api/tastings/photos/{name}", include_in_schema=False)
def photo(name: str, size: Optional[Literal["thumb", "large"]] = None, v: Optional[str] = None):
    """The original, or with `size` a resized JPEG copy (the original when it can't be resized: SVG, a corrupt
    file...). Versioned URLs (`v`, see photos.url_for) change with the photo, so browsers may keep them for good."""
    path = os.path.join(photos.PHOTOS_DIR, name)
    ext = os.path.splitext(name)[1].lower()
    if os.path.basename(name) != name or ext not in photos.PHOTO_EXTS or not os.path.isfile(path):
        raise HTTPException(404, "Photo not found")
    headers = {"Cache-Control": "public, max-age=31536000, immutable"} if v else None
    if size and ext != ".svg":
        try:
            return FileResponse(photos.thumbnail(name, size), media_type="image/jpeg", headers=headers)
        except Exception:  # Pillow raises many kinds (UnidentifiedImageError, OSError, DecompressionBombError...)
            pass
    return FileResponse(path, headers=headers)


def short_wine(t: TastingNote):
    w = t.bottle.wine
    return {"producer": w.producer.name, "cuvee": w.cuvee or "", "vintage": vintage_label(w.vintage, w.disgorgement_date),
            "color": w.type, "wine_id": w.id, "score": scores.preferred_score(w.scores), "scores": scores.label(w.scores),
            "region": w.region_obj.name if w.region_obj else None, "appellation": w.appellation.name if w.appellation else None}


@router.get("/api/tastings/{tasting_id}")
def tasting_detail(tasting_id: int, session: Session = Depends(get_session)):
    """One note with its place, bottle and wine; the rest of that occasion; other tastings of the wine (all vintages)."""
    t = (session.query(TastingNote)
         .options(joinedload(TastingNote.place), joinedload(TastingNote.bottle).joinedload(Bottle.wine).options(
             joinedload(Wine.producer), joinedload(Wine.region_obj), joinedload(Wine.appellation),
             joinedload(Wine.vineyard), joinedload(Wine.varietal)))
         .filter(TastingNote.id == tasting_id).first())
    if t is None:
        raise HTTPException(404, "Tasting not found")
    b, w = t.bottle, t.bottle.wine
    brief = (joinedload(TastingNote.place), joinedload(TastingNote.bottle).joinedload(Bottle.wine).joinedload(Wine.producer))

    # Same day, same place (or same free-text location when there is no place). `== None` renders IS NULL.
    same_place = TastingNote.place_id == t.place_id if t.place_id else TastingNote.location == t.location
    occasion = (session.query(TastingNote).options(*brief)
                .filter(TastingNote.date == t.date, same_place).order_by(TastingNote.sequence, TastingNote.id).all())

    # Same producer, cuvée, appellation and varietal
    related = session.query(Wine.id).filter(
        Wine.producer_id == w.producer_id, same_cuvee(w.cuvee),
        Wine.appellation_id == w.appellation_id, Wine.varietal_id == w.varietal_id)
    history = (session.query(TastingNote).options(*brief).join(Bottle)
               .filter(Bottle.wine_id.in_(related.scalar_subquery()), TastingNote.id != t.id)
               .order_by(TastingNote.date.desc(), TastingNote.id.desc()).all())

    vineyard = None
    if w.vineyard:
        v = w.vineyard
        vineyard = {"id": v.id, "label": vineyard_label(v)}
    return {
        "id": t.id, "date": iso(t.date), "seq": t.sequence, "glasses": t.glasses, "rating": t.rating,
        "notes": (t.notes or "").strip(), "tags": t.tags, "location": t.place.name if t.place else t.location,
        "styles": [s.tag for s in t.styles],
        "place": place_dict(t.place) if t.place else None,
        "photo": photo_url(photo_index(), t.place.name if t.place else t.location, t.date),
        "bottle": {
            "id": b.id, "format": b.bottle_size, "location": b.location, "qty": b.qty, "vendor": b.vendor,
            "provenance": b.provenance, "price": b.price, "currency": b.currency,
            "price_base": round(to_base(b.price, b.currency), 2) if b.price else None, "purchase_date": iso(b.purchase_date),
        },
        "wine": {
            "id": w.id, "producer_id": w.producer_id, "producer": w.producer.name, "cuvee": w.cuvee or "",
            "vintage": vintage_label(w.vintage, w.disgorgement_date), "disgorged": w.disgorgement_date, "color": w.type,
            "region": w.region_obj.name if w.region_obj else None, "region_color": w.region_obj.color if w.region_obj else None,
            "appellation": {"id": w.appellation.id, "name": w.appellation.name} if w.appellation else None,
            "vineyard": vineyard, "varietal": w.varietal.name if w.varietal else None, "blend": w.blend, "lwin": w.lwin,
            "grapes": [{"id": g.varietal_id, "name": g.varietal.name, "share": g.share} for g in w.grapes if g.varietal],
            "scores": scores.listing(w.scores),
            "drink_from": w.drink_window_start, "drink_to": w.drink_window_end,
        },
        "occasion": [{"id": o.id, "seq": o.sequence, "glasses": o.glasses, "rating": o.rating,
                      "notes": (o.notes or "").strip(), **short_wine(o)} for o in occasion],
        "history": [{"id": h.id, "date": iso(h.date), "place": h.place.name if h.place else h.location,
                     "place_id": h.place_id, "rating": h.rating, "notes": (h.notes or "").strip(), **short_wine(h)}
                    for h in history],
    }
