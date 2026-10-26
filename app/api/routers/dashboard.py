"""Home page: the cellar at a glance, recent tastings and purchases, and regions waiting to be opened."""
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from cellar import load_cellar, to_base
from db import Bottle, Region, TastingNote, Wine, get_session
from display import iso, vintage_label
from routers.forms import CONSUMED
import scores


router = APIRouter()

RECENT_OCCASIONS = 6
WINES_PER_OCCASION = 5
RECENT_PURCHASES = 8
# A region you hold bottles from but haven't opened anything from in this long gets a nudge
NUDGE_AFTER = timedelta(days=365)
NUDGES = 4


def _wine(w):
    return {"wine_id": w.id, "producer_id": w.producer_id, "producer": w.producer.name, "cuvee": w.cuvee or "",
            "appellation": w.appellation.name if w.appellation else None,
            "varietal": w.varietal.name if w.varietal else None, "score": scores.preferred_score(w.scores),
            "scores": scores.label(w.scores),
            "vintage": vintage_label(w.vintage, w.disgorgement_date), "color": w.type,
            "region": w.region_obj.name if w.region_obj else None}


def _occasions(session):
    """The latest evenings: tastings grouped by day and place, newest first."""
    notes = (session.query(TastingNote)
             .options(joinedload(TastingNote.place),
                      joinedload(TastingNote.bottle).joinedload(Bottle.wine).options(
                          joinedload(Wine.producer), joinedload(Wine.region_obj),
                          joinedload(Wine.appellation), joinedload(Wine.varietal)))
             .order_by(TastingNote.date.desc(), TastingNote.sequence, TastingNote.id)
             .limit(RECENT_OCCASIONS * WINES_PER_OCCASION * 2).all())
    occasions = {}
    for t in notes:
        place = t.place.name if t.place else (t.location or "Unknown")
        key = (iso(t.date), t.place_id or place)
        if key not in occasions:
            if len(occasions) == RECENT_OCCASIONS:
                break
            occasions[key] = {"date": iso(t.date), "place": place, "place_id": t.place_id,
                              "stars": t.place.michelin_stars if t.place else None, "wines": [], "count": 0}
        o = occasions[key]
        o["count"] += 1
        if len(o["wines"]) < WINES_PER_OCCASION:
            o["wines"].append({"id": t.id, "format": t.bottle.bottle_size, **_wine(t.bottle.wine)})
    return list(occasions.values())


def _purchases(session):
    """The latest bottles bought (by purchase date, then most recently added). Bottles logged only to
    record a tasting (location "Consumed", none left) aren't purchases."""
    rows = (session.query(Bottle)
            .options(joinedload(Bottle.wine).options(joinedload(Wine.producer), joinedload(Wine.region_obj),
                                                     joinedload(Wine.appellation), joinedload(Wine.varietal)))
            .filter((Bottle.location != CONSUMED) | Bottle.location.is_(None) | (Bottle.qty > 0))
            .order_by(Bottle.purchase_date.is_(None), Bottle.purchase_date.desc(), Bottle.id.desc())
            .limit(RECENT_PURCHASES).all())
    return [{"bottle_id": b.id, "date": iso(b.purchase_date), "qty": b.qty, "location": b.location, "format": b.bottle_size,
             "price": b.price, "currency": b.currency, "price_base": round(to_base(b.price, b.currency), 2) if b.price else None,
             **_wine(b.wine)} for b in rows]


def _nudges(session, bottles, today):
    """Regions you hold bottles from but haven't tasted anything from in a year (or ever), most bottles first."""
    held = {}
    for b in bottles:
        held[b["region"]] = held.get(b["region"], 0) + b["qty"]
    last = dict(session.query(Region.name, func.max(TastingNote.date)).select_from(TastingNote)
                .join(Bottle, TastingNote.bottle_id == Bottle.id).join(Wine, Bottle.wine_id == Wine.id)
                .join(Region, Wine.region_id == Region.id).group_by(Region.name).all())
    colors = dict(session.query(Region.name, Region.color).all())
    out = []
    for region, qty in held.items():
        if region == "Unknown":
            continue
        seen = last.get(region)
        if seen is None or today - seen > NUDGE_AFTER:
            out.append({"region": region, "color": colors.get(region), "bottles": qty, "last_tasted": iso(seen)})
    out.sort(key=lambda n: -n["bottles"])
    return out[:NUDGES]


DRINK_SOON = 8


def _drink_soon(bottles, today):
    """Cellar lines to open first: past their drinking window, then those whose window closes soonest.
    Also how many bottles stand where in their window."""
    year = today.year
    windowed = [b for b in bottles if b["maturity"] in ("ready", "past")]
    windowed.sort(key=lambda b: (b["maturity"] != "past", b["drink_to"] or 9999, -b["qty"]))
    lines = [{"bottle_id": b["bottle_id"], "wine_id": b["wine_id"], "producer": b["producer"], "cuvee": b["cuvee"],
              "appellation": b["appellation"], "varietal": b["varietal"], "vintage": b["vintage"], "color": b["color"],
              "region": b["region"], "qty": b["qty"], "location": b["location"], "format": b["format"],
              "score": b["score"], "scores": b["scores"],
              "drink_from": b["drink_from"], "drink_to": b["drink_to"], "maturity": b["maturity"],
              "years_left": (b["drink_to"] - year) if b["drink_to"] else None}
             for b in windowed[:DRINK_SOON]]
    counts = {k: sum(b["qty"] for b in bottles if b["maturity"] == k) for k in ("ready", "young", "past")}
    counts["unknown"] = sum(b["qty"] for b in bottles if b["maturity"] is None)
    return {"lines": lines, "bottles": counts}


@router.get("/api/dashboard")
def dashboard(session: Session = Depends(get_session)):
    today = date.today()
    bottles, _ = load_cellar(session)
    year_start = date(today.year, 1, 1)
    tasted_this_year = session.query(func.count(TastingNote.id)).filter(TastingNote.date >= year_start).scalar()
    purchases_this_year = session.query(func.count(Bottle.id)).filter(Bottle.purchase_date >= year_start).scalar()
    return {
        "today": today.isoformat(),
        "cellar": {
            "bottles": sum(b["qty"] for b in bottles),
            "cost": round(sum(b["qty"] * b["price_base"] for b in bottles)),
            "market": round(sum(b["qty"] * b["market_base"] for b in bottles)),
        },
        "year": {"tastings": tasted_this_year, "purchases": purchases_this_year},
        "occasions": _occasions(session),
        "purchases": _purchases(session),
        "nudges": _nudges(session, bottles, today),
        "drink_soon": _drink_soon(bottles, today),
    }
