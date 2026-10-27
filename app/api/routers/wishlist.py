"""The wishlist: wines you'd like, with what you'd pay and their market price (priced like a bottle:
tasks.update_market_prices)."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

import scores
import settings
from cellar import to_base
from db import Bottle, Wine, WishlistItem, get_session, same, same_cuvee
from display import iso, vintage_label

router = APIRouter()


class WishIn(BaseModel):
    wine_id: int | None = None  # set when adding; ignored when editing
    any_vintage: bool = False
    bottle_size: str | None = None
    target_price: float | None = Field(None, ge=0)
    currency: str | None = None
    note: str | None = None
    url: str | None = None


def _owned(session, item):
    """Bottles of it in the cellar: of that wine, or of any vintage of the cuvée."""
    w = item.wine
    query = session.query(func.coalesce(func.sum(Bottle.qty), 0)).join(Wine).filter(Bottle.qty > 0)
    if item.any_vintage:
        query = query.filter(Wine.producer_id == w.producer_id, same_cuvee(w.cuvee),
                             same(Wine.appellation_id, w.appellation_id), same(Wine.varietal_id, w.varietal_id))
    else:
        query = query.filter(Wine.id == w.id)
    return int(query.scalar())


def item_json(session, item):
    w = item.wine
    currency = (item.currency or settings.current.currency).upper()
    price, target = item.last_price, item.target_price
    return {
        "id": item.id, "wine_id": w.id, "producer": w.producer.name if w.producer else "", "producer_id": w.producer_id,
        "cuvee": w.cuvee or "", "vintage": vintage_label(w.vintage, w.disgorgement_date), "color": w.type,
        "region": w.region_obj.name if w.region_obj else None,
        "appellation": w.appellation.name if w.appellation else None, "lwin": w.lwin,
        "scores": scores.label(w.scores),
        "any_vintage": item.any_vintage, "bottle_size": item.bottle_size or "75cl",
        "target_price": target, "currency": currency, "note": item.note, "url": item.url, "added": iso(item.added),
        "market": {"price": price, "date": iso(item.last_price_date), "source": item.last_price_source} if price else None,
        # in the main currency, to sort and total
        "market_base": round(to_base(price, currency), 2) if price else None,
        "below_target": bool(price and target and price <= target),
        "owned": _owned(session, item),
    }


def _item(session, item_id):
    item = (session.query(WishlistItem).options(joinedload(WishlistItem.wine).joinedload(Wine.producer))
            .filter(WishlistItem.id == item_id).one_or_none())
    if item is None:
        raise HTTPException(404, "Not on the wishlist")
    return item


def _fill(item, data: WishIn):
    item.any_vintage = data.any_vintage
    item.bottle_size = (data.bottle_size or "").strip() or "75cl"
    item.target_price = data.target_price or None
    item.currency = (data.currency or "").strip().upper() or None
    item.note = (data.note or "").strip() or None
    item.url = (data.url or "").strip() or None


@router.get("/api/wishlist")
def wishlist(session: Session = Depends(get_session)):
    items = (session.query(WishlistItem).options(joinedload(WishlistItem.wine).joinedload(Wine.producer))
             .order_by(WishlistItem.added.desc().nullslast(), WishlistItem.id.desc()).all())
    return {"items": [item_json(session, i) for i in items]}


@router.post("/api/wishlist")
def add(data: WishIn, session: Session = Depends(get_session)):
    """Adds a wine (or, when it's already there, updates its entry)."""
    wine = session.get(Wine, data.wine_id) if data.wine_id else None
    if wine is None:
        raise HTTPException(404, "Wine not found")
    item = wine.wishlist or WishlistItem(wine=wine, added=date.today())
    _fill(item, data)
    session.add(item)
    session.commit()
    return item_json(session, item)


@router.put("/api/wishlist/{item_id}")
def edit(item_id: int, data: WishIn, session: Session = Depends(get_session)):
    item = _item(session, item_id)
    size, currency = item.bottle_size, item.currency
    _fill(item, data)
    if (item.bottle_size, item.currency) != (size, currency):  # the market price was for another size or currency
        item.last_price = item.last_price_date = item.last_price_source = None
    session.commit()
    return item_json(session, item)


@router.delete("/api/wishlist/{item_id}")
def remove(item_id: int, session: Session = Depends(get_session)):
    item = _item(session, item_id)
    session.delete(item)
    session.commit()
    return {"deleted": item_id}


@router.post("/api/wishlist/{item_id}/price")
def fetch_price(item_id: int, session: Session = Depends(get_session)):
    """Its market price now, as a bottle's (Bordeaux Index, else WineLabs.ai): the entry, with "log" saying why
    there's none."""
    from tasks import update_market_prices as prices
    item = _item(session, item_id)
    if not item.wine.lwin:
        raise HTTPException(400, "This wine has no LWIN: set one in the wine form (Suggest) to get its market price")
    if not prices.pricing_available():
        raise HTTPException(400, "No price source: set WINELABS_API_KEY or the Bordeaux Index login (Settings › Integrations)")
    lines = []
    from tasks import bordeaux_index as bi
    market = {} if bi.configured() else None
    prices.price_bottle(item, log=lines.append, bi=prices.bi_quotes(lines.append), market=market)
    session.commit()
    return {**item_json(session, item), "log": lines}
