"""Lookups against outside services, on demand: a bottle's market price (Bordeaux Index, else WineLabs.ai) and place coordinates
(OpenStreetMap). The shared code is in app/api/tasks/ (update_market_prices.py, geocode.py)."""
import logging
import urllib.error
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from db import Bottle, Wine, get_session

router = APIRouter()
log = logging.getLogger(__name__)


class PriceLine(BaseModel):
    bottle_id: int
    price: float
    source: str


class SavePrices(BaseModel):
    prices: list[PriceLine]


@router.post("/api/bottles/{bottle_id}/market-price")
def market_price(bottle_id: int, session: Session = Depends(get_session)):
    """Asks for the market price (by the wine's LWIN) of this bottle and of every other bottle of the same wine still
    in the cellar, whatever their price's age, and returns them for a look before saving (nothing is saved: see
    /market-price/save): Bordeaux Index (your portfolio, else the LiveTrade market for its LWIN18), else WineLabs.ai
    (one call per currency; scaled to each bottle's format)."""
    from tasks import bordeaux_index as bi_api
    from tasks import update_market_prices as prices
    b = (session.query(Bottle).options(joinedload(Bottle.wine).joinedload(Wine.producer))
         .filter(Bottle.id == bottle_id).one_or_none())
    if b is None:
        raise HTTPException(404, "Bottle not found")
    if not b.wine or not b.wine.lwin:
        raise HTTPException(422, "This wine has no LWIN: add one on the wine's edit page first")
    if not prices.pricing_available():
        raise HTTPException(503, "No price source on the server: add WINELABS_API_KEY=… (or the BI_ login) to "
                                 ".secrets.env and restart the app")
    lines, cache = [], {}
    bi = prices.bi_quotes(log=lines.append)
    market = {} if bi_api.configured() else None  # the LiveTrade market, for wines not in your portfolio
    others = (session.query(Bottle).filter(Bottle.wine_id == b.wine_id, Bottle.id != b.id, Bottle.qty > 0)
              .order_by(Bottle.id).all())
    proposals = []
    for o in [b, *others]:
        old = {"old": o.last_price, "old_date": o.last_price_date.isoformat() if o.last_price_date else None,
               "old_source": o.last_price_source}
        log_to = lines.append if o is b else (lambda line: None)
        new = prices.price_bottle(o, cache, log=log_to, bi=bi, market=market)
        proposals.append({"bottle_id": o.id, "this": o is b, "location": o.location, "bottle_size": o.bottle_size,
                          "qty": o.qty, "currency": o.currency, **old, "new": new,
                          "source": o.last_price_source if new is not None else None})
    session.rollback()  # a look first: saved by /market-price/save
    found = any(p["new"] is not None for p in proposals)
    message = None
    if proposals[0]["new"] is None:
        message = next((line.split("]", 1)[-1].strip() for line in lines if "[" in line), "No price found")
    return {"found": found, "message": message, "prices": proposals}


@router.post("/api/bottles/{bottle_id}/market-price/save")
def save_market_price(bottle_id: int, body: SavePrices, session: Session = Depends(get_session)):
    """Saves the prices the preview proposed (no new request): only on bottles of this bottle's wine."""
    b = session.get(Bottle, bottle_id)
    if b is None:
        raise HTTPException(404, "Bottle not found")
    now, saved = datetime.now(), 0
    for line in body.prices:
        o = session.get(Bottle, line.bottle_id)
        if o is None or o.wine_id != b.wine_id or line.price <= 0:
            continue
        o.last_price, o.last_price_date, o.last_price_source = line.price, now, line.source
        saved += 1
    session.commit()
    return {"saved": saved}


@router.get("/api/lookups/lwin")
def lwin(producer: str, cuvee: str = "", appellation: str = ""):
    """LWIN candidates for a wine from the Liv-ex list (data/lwin/lwin.sqlite, built on a PC by match_lwin.py
    --build-index): {"available", "suggestions": [{"lwin", "name", "colour", "match"}]}."""
    from tasks import match_lwin
    try:
        entries = match_lwin.entries_for(producer)
    except FileNotFoundError:
        return {"available": False, "suggestions": []}
    found = match_lwin.suggest(entries, producer, cuvee, appellation)
    return {"available": True, "suggestions": [
        {"lwin": e["lwin"], "name": e["display_name"], "colour": e.get("colour"), "match": kind} for e, kind, _ in found]}


@router.get("/api/lookups/geocode")
def geocode(q: str):
    """Places matching a free-text query on OpenStreetMap: [{"name", "address", "lat", "lng", "category", "type"}]."""
    from tasks.geocode import search
    if not q.strip():
        return []
    try:
        return search(q.strip())
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        log.info("OpenStreetMap lookup failed: %s", e)
        raise HTTPException(502, "OpenStreetMap couldn't be reached")
