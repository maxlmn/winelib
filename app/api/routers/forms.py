"""Forms: create / update / delete producers, wines, bottles, tastings, places and visits, plus the
lookups the forms type-ahead against.

Related rows are referenced by id, or named to be created: `"producer": 12` picks producer 12,
`"producer": {"name": "Domaine X", "region": 3}` gets or creates it (matched by name, ignoring case).
"""
import re
from datetime import date as Date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import AfterValidator, BaseModel, BeforeValidator, Field, field_validator, model_validator
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

import geo
import maplinks
import photos
import settings
from cellar import location_sort_key
from display import vineyard_label
from textsearch import fold, search
from tasks.matching import is_rose
from tasks.blends import BLEND_STYLES, blend_style
import style_tags
from db import same, Appellation, Bottle, BottleEvent, TastingTag, WineTag, ListItem, Place, Producer, Region, RestaurantVisit, TastingNote, Varietal, Vineyard, Wine, get_session, same_cuvee

router = APIRouter()

WINE_TYPES = ["Red", "White", "Bubbles", "Bubbles Rose", "Rose", "Sweet", "Orange", "Fortified"]
BOTTLE_SIZES = ["75cl", "37.5cl", "150cl", "300cl", "600cl"]
CURRENCIES = ["EUR", "USD", "GBP"]  # offered with the main currency and those with a rate
PRODUCER_TYPES = ["domaine", "maison", "negoce"]
PLACE_TYPES = ["Restaurant", "Winery", "Home", "Bar", "Friend's Place", "Other"]
AD_HOC = "Ad-Hoc"  # provenance of a bottle created to log a tasting of a wine not from the cellar
CONSUMED = "Consumed"  # location of those bottles
LOOKUP_LIMIT = 20


# --- Input models -----------------------------------------------------------------------------

def _blank_to_none(v):
    if isinstance(v, str):
        v = v.strip()
        return v or None
    return v


Text = Annotated[str | None, BeforeValidator(_blank_to_none)]
Name = Annotated[str, BeforeValidator(_blank_to_none), Field(min_length=1)]


class NewName(BaseModel):
    name: Name


class NewProducer(BaseModel):
    name: Name
    region: int | NewName | None = None


FRIENDS = "Friend's Place"


class PlaceFields(BaseModel):
    name: Name
    city: Text = None
    country: Text = None
    type: Text = None

    @model_validator(mode="after")
    def at_a_friends(self):
        """"@Mia": a friend's home, shown as a house and who it is (Mia)"""
        if self.name.startswith("@") and self.name[1:].strip():
            self.name, self.type = self.name[1:].strip(), FRIENDS
        return self


class GrapeIn(BaseModel):
    """One of a wine's grapes: an existing grape (id) or a new one (name), and its share in percent when known."""
    varietal: int | NewName
    share: float | None = Field(None, gt=0, le=100)


class WineIn(BaseModel):
    producer: int | NewProducer
    cuvee: Text = None
    vintage: Text = None
    type: Literal[tuple(WINE_TYPES)] = "Red"
    disgorgement_date: Text = None
    region: int | NewName | None = None
    appellation: int | NewName | None = None
    varietal: int | NewName | None = None  # the main grape alone (older clients); `grapes` wins when given
    grapes: list[GrapeIn] | None = None  # its grapes in order, the first the main one
    vineyard: int | str | None = None  # a vineyard, or a lieu-dit of the map store: "lieu_dit:49060:les-poyeux"
    blend: Text = None  # its style: one of BLEND_STYLES (an older text is read: "Bordeaux Blend")
    lwin: Text = None
    drink_window_start: int | None = Field(None, ge=1900, le=2200)
    drink_window_end: int | None = Field(None, ge=1900, le=2200)

    @field_validator("drink_window_start", "drink_window_end", mode="before")
    @classmethod
    def zero_is_unset(cls, v):
        return None if v in (0, "", "0") else v


def currencies():
    """The main currency first, then the usual ones and any with an exchange rate in the settings."""
    return list(dict.fromkeys([settings.current.currency] + CURRENCIES + list(settings.current.exchange_rates)))


def _check_currency(v):
    # Prices are valued in the main currency with the settings' rates, so a currency needs one
    rates = settings.current.exchange_rates
    if v not in rates:
        raise ValueError(f"Unknown currency {v!r} (use one of {', '.join(rates)}, or add its rate in Settings)")
    return v


Currency = Annotated[str, AfterValidator(_check_currency)]


class BottleDetails(BaseModel):
    bottle_size: Name = "75cl"
    price: float | None = Field(None, ge=0)
    currency: Currency | None = None  # the main currency when not given
    vendor: Text = None
    provenance: Text = None
    purchase_date: Date | None = None


class BottleIn(BottleDetails):
    wine: int | WineIn
    qty: int = Field(1, ge=0)
    location: Text = None
    last_price: float | None = Field(None, ge=0)
    last_price_date: Date | None = None
    last_price_source: Text = None


class ProducerIn(BaseModel):
    name: Name
    region: int | NewName | None = None
    subregion: Text = None
    village: Text = None
    winemaker: Text = None
    owner: Text = None
    type: Annotated[Literal[tuple(PRODUCER_TYPES)] | None, BeforeValidator(_blank_to_none)] = None
    importers: Text = None
    lists: Text = None
    profile_url: Text = None
    website: Text = None
    notes: Text = None
    description: Text = None
    aliases: Text = None


class TastingIn(BaseModel):
    date: Date
    place: int | PlaceFields | None = None
    rating: int | None = Field(None, ge=50, le=100)
    glasses: float | None = Field(1.0, ge=0, le=50)
    sequence: int | None = Field(1, ge=0)
    tags: Text = None
    notes: Text = None
    bottle: BottleDetails | None = None  # other wine: the ad-hoc bottle; edit: the tasted bottle's details
    styles: list[str] | None = None  # the wine's style found ("fresh", "mineral"); None: left as it is


class TastingCreate(TastingIn):
    source: Literal["cellar", "other"]
    bottle_id: int | None = None  # cellar
    consume: bool = True  # cellar: take one bottle out of stock
    wine: int | WineIn | None = None  # other


class PlaceIn(PlaceFields):
    michelin_stars: int | None = Field(None, ge=0, le=3)
    notes: Text = None
    lat: float | None = Field(None, ge=-90, le=90)
    lng: float | None = Field(None, ge=-180, le=180)

    @field_validator("lat", "lng", mode="before")
    @classmethod
    def zero_is_unset(cls, v):
        return None if v in (0, "", None) else v


class VisitIn(BaseModel):
    date: Date
    place: int | PlaceFields
    notes: Text = None


# --- Write helpers ----------------------------------------------------------------------------

def _get(session, model, id_, label):
    row = session.get(model, id_)
    if row is None:
        raise HTTPException(404, f"{label} #{id_} not found")
    return row


def _by_name(session, model, name):
    return session.query(model).filter(func.lower(model.name) == name.lower()).first()


def _get_or_create(session, model, name, **fields):
    row = _by_name(session, model, name)
    if row is None:
        row = model(name=name, **fields)
        session.add(row)
        session.flush()
    return row


def _region(session, ref):
    if ref is None:
        return None
    if isinstance(ref, int):
        return _get(session, Region, ref, "Region")
    return _get_or_create(session, Region, ref.name)


def _producer(session, ref):
    if isinstance(ref, int):
        return _get(session, Producer, ref, "Producer")
    return _get_or_create(session, Producer, ref.name, region_obj=_region(session, ref.region))


def _appellation(session, ref, region):
    if ref is None:
        return None
    if isinstance(ref, int):
        return _get(session, Appellation, ref, "Appellation")
    # A new appellation belongs to the wine's region
    return _get_or_create(session, Appellation, ref.name, region_obj=region)


def _varietal(session, ref):
    if ref is None:
        return None
    if isinstance(ref, int):
        return _get(session, Varietal, ref, "Varietal")
    return _get_or_create(session, Varietal, ref.name)


def _place(session, ref):
    if ref is None:
        return None
    if isinstance(ref, int):
        return _get(session, Place, ref, "Place")
    return _get_or_create(session, Place, ref.name, city=ref.city, country=ref.country, type=ref.type)


def _vineyard(session, ref, region):
    """A vineyard by id, or a lieu-dit picked in the form (made a vineyard, once)"""
    if isinstance(ref, str):
        import lieux_dits
        found = lieux_dits.find(ref.removeprefix("lieu_dit:"))
        if found is None:
            raise HTTPException(422, "No such lieu-dit in the map store")
        return lieux_dits.vineyard(session, ref.removeprefix("lieu_dit:"), *found, region.id if region else None)
    return _get(session, Vineyard, ref, "Vineyard")


def _fill_wine(session, w, data: WineIn):
    # Resolve (and create) everything first: w may be a new, not yet added Wine
    producer, region = _producer(session, data.producer), _region(session, data.region)
    appellation = _appellation(session, data.appellation, region)
    grapes = [(_varietal(session, g.varietal), g.share) for g in data.grapes] if data.grapes is not None else None
    varietal = _varietal(session, data.varietal) if grapes is None else None
    vineyard = _vineyard(session, data.vineyard, region) if data.vineyard else None
    w.producer, w.region_obj, w.appellation, w.vineyard = producer, region, appellation, vineyard
    if grapes is not None:
        w.set_grapes(grapes)
    else:
        w.varietal = varietal
    # No cuvée name is '' like the rest of the cellar, not NULL
    w.cuvee, w.vintage, w.type = data.cuvee or "", data.vintage, data.type
    if w.type == "Bubbles" and is_rose(w.cuvee):  # "Brut Rosé", "Rosé de Saignée": a sparkling rosé
        w.type = "Bubbles Rose"
    w.disgorgement_date = data.disgorgement_date if (data.type or "").startswith("Bubbles") else None
    w.blend, w.lwin = blend_style(data.blend), data.lwin
    w.drink_window_start, w.drink_window_end = data.drink_window_start, data.drink_window_end
    return w


def _vintages(session, w):
    """The wine's other vintages, as the wine page lists them: same producer, cuvée, appellation and grape."""
    return (session.query(Wine)
            .filter(Wine.id != w.id, Wine.producer_id == w.producer_id, same_cuvee(w.cuvee),
                    same(Wine.appellation_id, w.appellation_id), same(Wine.varietal_id, w.varietal_id)))


def _wine(session, ref):
    """A wine by id, or a new one: without a vineyard given, its other vintages' when they all have the same."""
    if isinstance(ref, int):
        return _get(session, Wine, ref, "Wine")
    w = _fill_wine(session, Wine(), ref)
    session.add(w)
    session.flush()
    if w.vineyard_id is None:
        found = {v for (v,) in _vintages(session, w).with_entities(Wine.vineyard_id).filter(Wine.vineyard_id.isnot(None)).distinct()}
        if len(found) == 1:
            w.vineyard_id = found.pop()
            session.flush()
    return w


def _fill_bottle_details(b, d: BottleDetails):
    b.bottle_size, b.price, b.currency = d.bottle_size, d.price, d.currency or settings.current.currency
    b.vendor, b.provenance, b.purchase_date = d.vendor, d.provenance, d.purchase_date


def _unique_name(session, model, name, label, own_id=None):
    other = _by_name(session, model, name)
    if other is not None and other.id != own_id:
        raise HTTPException(409, f"A {label} named “{other.name}” already exists")


def _refuse_if(count, message):
    if count:
        raise HTTPException(409, message)


def _commit(session, row):
    session.commit()
    return row.id


# --- Producers --------------------------------------------------------------------------------

def _fill_producer(session, p, data: ProducerIn):
    for field in ("name", "subregion", "village", "winemaker", "owner", "type", "importers", "lists",
                  "profile_url", "website", "notes", "description"):
        setattr(p, field, getattr(data, field))
    p.aliases = _aliases(data.aliases)
    p.region_obj = _region(session, data.region)


def _aliases(text):
    """"Chave; JL Chave ,, " -> "Chave, JL Chave" (None when empty), each once."""
    seen, out = set(), []
    for a in re.split(r"[,;\n]", text or ""):
        a = " ".join(a.split())
        if a and a.lower() not in seen:
            seen.add(a.lower())
            out.append(a)
    return ", ".join(out) or None


class AliasIn(BaseModel):
    alias: Name


@router.post("/api/producers/{producer_id}/aliases")
def add_alias(producer_id: int, data: AliasIn, session: Session = Depends(get_session)):
    """Another name the producer goes by (an import's "this producer is…"), added to its aliases."""
    p = _get(session, Producer, producer_id, "Producer")
    p.aliases = _aliases(f"{p.aliases or ''}, {data.alias}")
    session.commit()
    return {"id": p.id, "aliases": p.aliases}


@router.post("/api/producers", status_code=201)
def create_producer(data: ProducerIn, session: Session = Depends(get_session)):
    _unique_name(session, Producer, data.name, "producer")
    p = Producer()
    _fill_producer(session, p, data)
    session.add(p)
    return {"id": _commit(session, p)}


@router.put("/api/producers/{producer_id}")
def update_producer(producer_id: int, data: ProducerIn, session: Session = Depends(get_session)):
    p = _get(session, Producer, producer_id, "Producer")
    _unique_name(session, Producer, data.name, "producer", p.id)
    _fill_producer(session, p, data)
    return {"id": _commit(session, p)}


@router.delete("/api/producers/{producer_id}")
def delete_producer(producer_id: int, session: Session = Depends(get_session)):
    p = _get(session, Producer, producer_id, "Producer")
    n = session.query(Wine).filter_by(producer_id=p.id).count()
    _refuse_if(n, f"{p.name} still has {n} wine{'s' * (n != 1)}: delete or move them first")
    session.query(ListItem).filter_by(producer_id=p.id).delete()  # off the lists it was on
    session.delete(p)
    session.commit()
    return {"deleted": producer_id}


@router.delete("/api/appellations/{appellation_id}")
def delete_appellation(appellation_id: int, session: Session = Depends(get_session)):
    """An appellation no wine uses any more (a typo, a duplicate)."""
    a = _get(session, Appellation, appellation_id, "Appellation")
    n = session.query(Wine).filter_by(appellation_id=a.id).count()
    _refuse_if(n, f"{a.name} still has {n} wine{'s' * (n != 1)}: give them another appellation first")
    region = a.region_obj.name if a.region_obj else None
    session.delete(a)
    session.commit()
    return {"deleted": appellation_id, "region": region}


class AppellationIn(BaseModel):
    name: Name
    region: int | NewName | None = None
    subregion: Text = None
    type: Text = None
    colors: Text = None
    varieties_text: Text = None
    location_link: Text = None
    details: Text = None
    aliases: Text = None


APPELLATION_FIELDS = ("name", "subregion", "type", "colors", "varieties_text", "location_link", "details", "aliases")


@router.put("/api/appellations/{appellation_id}")
def update_appellation(appellation_id: int, data: AppellationIn, session: Session = Depends(get_session)):
    """The appellation's own fields; the EU / INAO ones (PDO ID, yields, shapes) stay as imported."""
    a = _get(session, Appellation, appellation_id, "Appellation")
    _unique_name(session, Appellation, data.name, "appellation", a.id)
    for field in APPELLATION_FIELDS:
        setattr(a, field, getattr(data, field))
    a.aliases = _aliases(data.aliases)
    a.region_obj = _region(session, data.region)
    return {"id": _commit(session, a)}


# --- Critics' scores ---------------------------------------------------------------------------

class ScoreIn(BaseModel):
    critic: Name
    score: Text = None
    note: Text = None
    url: Text = None
    date: Date | None = None


@router.post("/api/wines/{wine_id}/scores")
def save_score(wine_id: int, data: ScoreIn, session: Session = Depends(get_session)):
    """A critic's score for the wine (added, or replacing that critic's): "Add a score" on the wine page."""
    w = _get(session, Wine, wine_id, "Wine")
    s = w.set_score(data.critic, data.score, data.note, data.url, data.date)
    session.commit()
    settings.adopt_critic(session, s.critic)
    return {"id": w.id, "critic": s.critic}


@router.delete("/api/wines/{wine_id}/scores")
def delete_score(wine_id: int, critic: str, session: Session = Depends(get_session)):
    w = _get(session, Wine, wine_id, "Wine")
    s = w.score_of(critic)
    if s is None:
        raise HTTPException(404, f"No score from {critic} for this wine")
    w.scores.remove(s)
    session.commit()
    return {"deleted": critic}


@router.get("/api/lookups/critics")
def lookup_critics(session: Session = Depends(get_session)):
    """The critics already in the database, most used first (for "Add a score")."""
    from db import CriticScore
    rows = (session.query(CriticScore.critic, func.count(CriticScore.id)).group_by(CriticScore.critic)
            .order_by(func.count(CriticScore.id).desc()).all())
    return [c for c, _ in rows]


# --- Vineyards --------------------------------------------------------------------------------

class VineyardIn(BaseModel):
    name: Name
    region: int | NewName | None = None
    sub_region: Text = None
    village: Text = None


@router.put("/api/vineyards/{vineyard_id}")
def update_vineyard(vineyard_id: int, data: VineyardIn, session: Session = Depends(get_session)):
    """Its name, region, sub-region and village (names needn't be unique: two regions can have the same one); its
    outline and external id stay. An outline drawn for it takes the new name."""
    from db import CustomShape
    v = _get(session, Vineyard, vineyard_id, "Vineyard")
    v.name, v.sub_region, v.village = data.name, data.sub_region, data.village
    v.region_obj = _region(session, data.region)
    if (sid := geo.custom_id(v.boundary)) and (shape := session.get(CustomShape, sid)):
        shape.name = v.name
    return {"id": _commit(session, v)}


@router.delete("/api/vineyards/{vineyard_id}")
def delete_vineyard(vineyard_id: int, session: Session = Depends(get_session)):
    """A vineyard no wine uses any more (a typo, a duplicate), with the outline drawn for it."""
    from db import CustomShape
    v = _get(session, Vineyard, vineyard_id, "Vineyard")
    n = session.query(Wine).filter_by(vineyard_id=v.id).count()
    _refuse_if(n, f"{v.name} still has {n} wine{'s' * (n != 1)}: give them another vineyard first")
    region = v.region_obj.name if v.region_obj else None
    sid = geo.custom_id(v.boundary)
    if sid and (shape := session.get(CustomShape, sid)):
        session.delete(shape)
    session.delete(v)
    session.commit()
    if sid:
        geo.custom_changed(sid)  # its outline drops out of the maps' cache too
    return {"deleted": vineyard_id, "region": region}


# --- Wines ------------------------------------------------------------------------------------

def _share_lwin(session, w):
    """An LWIN is the wine's, whatever the vintage: a wine without one takes its other vintages' (same producer,
    cuvée, appellation and colour); one with one gives it to those without. The number of other vintages given it."""
    from tasks.match_lwin import cuvee_key, lwin7
    others = [o for o in session.query(Wine).filter(Wine.producer_id == w.producer_id, Wine.id != w.id)
              if cuvee_key(o) == cuvee_key(w)]
    if not (w.lwin or "").strip():
        codes = {lwin7(o.lwin) for o in others if lwin7(o.lwin)}
        if len(codes) == 1:
            w.lwin = codes.pop()
        return 0
    code = lwin7(w.lwin)
    blank = [o for o in others if not (o.lwin or "").strip()]
    for o in blank if code else []:
        o.lwin = code
    return len(blank) if code else 0


@router.post("/api/wines", status_code=201)
def create_wine(data: WineIn, session: Session = Depends(get_session)):
    w = _wine(session, data)
    session.flush()
    _share_lwin(session, w)
    return {"id": _commit(session, w)}


@router.put("/api/wines/{wine_id}")
def update_wine(wine_id: int, data: WineIn, session: Session = Depends(get_session)):
    """The wine's fields. A new vineyard goes to its other vintages too (same producer, cuvée, appellation and grape,
    as the wine page lists them) that had the same vineyard as it before, or none; one with another vineyard keeps it."""
    w = _get(session, Wine, wine_id, "Wine")
    before = w.vineyard_id
    vintages = (_vintages(session, w)
                .filter((Wine.vineyard_id.is_(None)) | (Wine.vineyard_id == before) if before else Wine.vineyard_id.is_(None))
                .all())
    _fill_wine(session, w, data)
    changed = (w.vineyard.id if w.vineyard else None) != before
    for other in vintages if changed else []:
        other.vineyard = w.vineyard
    session.flush()
    _share_lwin(session, w)
    return {"id": _commit(session, w), "vintages_updated": len(vintages) if changed else 0}


@router.delete("/api/wines/{wine_id}")
def delete_wine(wine_id: int, session: Session = Depends(get_session)):
    w = _get(session, Wine, wine_id, "Wine")
    n = session.query(Bottle).filter_by(wine_id=w.id).count()
    _refuse_if(n, f"This wine still has {n} bottle{'s' * (n != 1)} (in the cellar or tasted): delete them first")
    producer_id = w.producer_id
    session.query(ListItem).filter_by(wine_id=w.id).delete()  # off the lists it was on
    session.query(WineTag).filter_by(wine_id=w.id).delete()  # and its style tags
    session.delete(w)
    session.commit()
    return {"deleted": wine_id, "producer_id": producer_id}


# --- Bottles ----------------------------------------------------------------------------------

def _fill_bottle(session, b, data: BottleIn):
    b.wine = _wine(session, data.wine)
    _fill_bottle_details(b, data)
    b.qty, b.location = data.qty, data.location
    b.last_price, b.last_price_date, b.last_price_source = data.last_price or None, data.last_price_date, data.last_price_source


@router.post("/api/bottles", status_code=201)
def create_bottle(data: BottleIn, session: Session = Depends(get_session)):
    b = Bottle()
    _fill_bottle(session, b, data)
    session.add(b)
    return {"id": _commit(session, b), "wine_id": b.wine_id}


@router.put("/api/bottles/{bottle_id}")
def update_bottle(bottle_id: int, data: BottleIn, session: Session = Depends(get_session)):
    b = _get(session, Bottle, bottle_id, "Bottle")
    _fill_bottle(session, b, data)
    return {"id": _commit(session, b), "wine_id": b.wine_id}


@router.delete("/api/bottles/{bottle_id}")
def delete_bottle(bottle_id: int, session: Session = Depends(get_session)):
    b = _get(session, Bottle, bottle_id, "Bottle")
    n = session.query(TastingNote).filter_by(bottle_id=b.id).count()
    _refuse_if(n, f"This bottle has {n} tasting note{'s' * (n != 1)}: delete them first")
    wine_id = b.wine_id
    session.delete(b)
    session.commit()
    return {"deleted": bottle_id, "wine_id": wine_id}


# --- A lieu-dit as a wine's vineyard (from its map) ----------------------------------------------

class LieuDitIn(BaseModel):
    lieu_dit: str  # the store's id: "49060:les-poyeux" (or "lieu_dit:49060:les-poyeux")


@router.post("/api/wines/{wine_id}/lieu-dit")
def set_lieu_dit(wine_id: int, data: LieuDitIn, session: Session = Depends(get_session)):
    """The cadastre's lieu-dit as this wine's vineyard, and its cuvée's other vintages' with no vineyard (or the
    same one as this wine)."""
    import lieux_dits
    w = _get(session, Wine, wine_id, "Wine")
    sid = data.lieu_dit.removeprefix("lieu_dit:")
    found = lieux_dits.find(sid)
    if found is None:
        raise HTTPException(404, "No such lieu-dit in the map store")
    name, details = found
    before = w.vineyard_id
    vintages = (session.query(Wine).filter(Wine.producer_id == w.producer_id, same_cuvee(w.cuvee),
                                           Wine.appellation_id == w.appellation_id).all())
    wines = [x for x in vintages if x.id == w.id or x.vineyard_id is None or (before and x.vineyard_id == before)]
    v = lieux_dits.link(session, wines, sid, name, details)
    session.commit()
    return {"vineyard_id": v.id, "name": v.name, "wines": len(wines)}


@router.post("/api/vineyards/{vineyard_id}/lieu-dit")
def set_vineyard_lieu_dit(vineyard_id: int, data: LieuDitIn, session: Session = Depends(get_session)):
    """The cadastre's lieu-dit as this vineyard's outline (its wines keep it as their vineyard); an outline drawn
    for it goes. Refused when another vineyard is that lieu-dit already."""
    import lieux_dits
    from db import CustomShape
    v = _get(session, Vineyard, vineyard_id, "Vineyard")
    sid = data.lieu_dit.removeprefix("lieu_dit:")
    found = lieux_dits.find(sid)
    if found is None:
        raise HTTPException(404, "No such lieu-dit in the map store")
    boundary = f"lieu_dit:{sid}"
    other = session.query(Vineyard).filter(Vineyard.boundary == boundary, Vineyard.id != v.id).first()
    _refuse_if(other, f"{other.name if other else ''} is already this lieu-dit's vineyard: give its wines that one instead")
    drawn = geo.custom_id(v.boundary)
    if drawn and (shape := session.get(CustomShape, drawn)):
        session.delete(shape)
    v.boundary = boundary
    v.village = v.village or found[1].get("commune_name")
    session.commit()
    if drawn:
        geo.custom_changed(drawn)
    return {"vineyard_id": v.id, "lieu_dit": sid}


# --- Style tags -------------------------------------------------------------------------------

class TagsIn(BaseModel):
    tags: list[str]


@router.get("/api/tags")
def tags(session: Session = Depends(get_session)):
    """The style vocabulary, and every tag in use with how many wines carry it."""
    return {"vocabulary": style_tags.VOCABULARY, "used": style_tags.used(session)}


@router.put("/api/wines/{wine_id}/tags")
def set_wine_tags(wine_id: int, data: TagsIn, session: Session = Depends(get_session)):
    """The style tags set on a wine by hand (its tastings' are theirs, gathered when shown)."""
    w = _get(session, Wine, wine_id, "Wine")
    session.query(WineTag).filter_by(wine_id=w.id).delete()
    session.add_all(WineTag(wine_id=w.id, tag=t) for t in style_tags.clean(data.tags))
    session.commit()
    return {"wine_id": w.id, "tags": style_tags.of_wines(session, [w.id]).get(w.id, [])}


class DrinkWindowIn(BaseModel):
    start: int | None = Field(None, ge=1900, le=2200)
    end: int | None = Field(None, ge=1900, le=2200)

    @field_validator("start", "end", mode="before")
    @classmethod
    def zero_is_unset(cls, v):
        return None if v in (0, "", "0") else v


@router.put("/api/wines/{wine_id}/drink-window")
def set_drink_window(wine_id: int, data: DrinkWindowIn, session: Session = Depends(get_session)):
    """The years to drink a wine in, as you set them (its page's menu): either may be left open, both cleared."""
    if data.start and data.end and data.end < data.start:
        raise HTTPException(422, "The window ends before it starts")
    w = _get(session, Wine, wine_id, "Wine")
    w.drink_window_start, w.drink_window_end = data.start, data.end
    session.commit()
    return {"wine_id": w.id, "drink_window": [w.drink_window_start, w.drink_window_end]}


# Bottles that leave other than by being drunk (that's a tasting): taken off the count, put back if undone
OUT_KINDS = ("gifted", "sold", "broken", "other")


class BottleOutIn(BaseModel):
    kind: Literal["gifted", "sold", "broken", "other"]
    qty: int = Field(1, ge=1)
    date: Date | None = None
    note: Annotated[str | None, BeforeValidator(_blank_to_none)] = None
    price: float | None = Field(None, ge=0)  # a bottle, when sold
    currency: Annotated[str | None, BeforeValidator(_blank_to_none)] = None


@router.post("/api/bottles/{bottle_id}/out", status_code=201)
def bottle_out(bottle_id: int, data: BottleOutIn, session: Session = Depends(get_session)):
    """Some of these bottles gifted, sold, broken...: recorded, and taken off the count."""
    b = _get(session, Bottle, bottle_id, "Bottle")
    if data.qty > (b.qty or 0):
        raise HTTPException(409, f"Only {b.qty or 0} left in the cellar")
    b.qty -= data.qty
    e = BottleEvent(bottle=b, kind=data.kind, qty=data.qty, date=data.date or Date.today(), note=data.note,
                    price=data.price if data.kind == "sold" else None,
                    currency=(data.currency or b.currency) if data.kind == "sold" and data.price is not None else None)
    session.add(e)
    session.commit()
    return {"id": e.id, "bottle_id": b.id, "qty": b.qty}


@router.delete("/api/bottles/{bottle_id}/out/{event_id}")
def bottle_back(bottle_id: int, event_id: int, session: Session = Depends(get_session)):
    """Undo: the bottles back in the cellar, the record gone."""
    e = _get(session, BottleEvent, event_id, "Record")
    if e.bottle_id != bottle_id:
        raise HTTPException(404, f"Record #{event_id} not found on this bottle")
    e.bottle.qty = (e.bottle.qty or 0) + e.qty
    qty = e.bottle.qty
    session.delete(e)
    session.commit()
    return {"bottle_id": bottle_id, "qty": qty}


# --- Tastings ---------------------------------------------------------------------------------

def _fill_tasting(session, tn, data: TastingIn):
    place = _place(session, data.place)
    tn.place = place
    tn.location = place.name if place else "Unknown"
    tn.date, tn.rating, tn.glasses, tn.sequence = data.date, data.rating, data.glasses, data.sequence
    tn.tags, tn.notes = data.tags, data.notes
    if data.styles is not None:
        tn.styles = [TastingTag(tag=t) for t in style_tags.clean(data.styles)]


@router.post("/api/tastings", status_code=201)
def create_tasting(data: TastingCreate, session: Session = Depends(get_session)):
    if data.source == "cellar":
        if not data.bottle_id:
            raise HTTPException(422, "Pick the bottle from the cellar")
        bottle = _get(session, Bottle, data.bottle_id, "Bottle")
        if data.consume and (bottle.qty or 0) > 0:
            bottle.qty -= 1
    else:
        if data.wine is None:
            raise HTTPException(422, "Pick the wine, or create a new one")
        bottle = Bottle(wine=_wine(session, data.wine), qty=0, location=CONSUMED)
        _fill_bottle_details(bottle, data.bottle or BottleDetails(provenance=AD_HOC, purchase_date=Date.today()))
        session.add(bottle)
        session.flush()
    tn = TastingNote()
    _fill_tasting(session, tn, data)
    tn.bottle = bottle
    session.add(tn)
    return {"id": _commit(session, tn), "bottle_id": bottle.id, "wine_id": bottle.wine_id}


@router.put("/api/tastings/{tasting_id}")
def update_tasting(tasting_id: int, data: TastingIn, session: Session = Depends(get_session)):
    tn = _get(session, TastingNote, tasting_id, "Tasting note")
    _fill_tasting(session, tn, data)
    if data.bottle:
        _fill_bottle_details(tn.bottle, data.bottle)
    return {"id": _commit(session, tn), "bottle_id": tn.bottle_id, "wine_id": tn.bottle.wine_id}


def _is_adhoc(b):
    """A bottle recorded only for a tasting (a glass elsewhere, a friend's bottle): not one of the cellar's. The tasting
    form shows it as "other", deleting its last tasting deletes it"""
    return b.provenance == AD_HOC or b.location == CONSUMED


@router.delete("/api/tastings/{tasting_id}")
def delete_tasting(tasting_id: int, session: Session = Depends(get_session)):
    tn = _get(session, TastingNote, tasting_id, "Tasting note")
    b = tn.bottle
    session.delete(tn)
    session.flush()
    # The ad-hoc bottle existed only for this note. A cellar bottle keeps its quantity: we can't tell if it was drunk.
    adhoc = b is not None and _is_adhoc(b) and not b.qty and not session.query(TastingNote).filter_by(bottle_id=b.id).count()
    if adhoc:
        session.delete(b)
    session.commit()
    return {"deleted": tasting_id, "bottle_deleted": adhoc, "wine_id": b.wine_id if b else None}


# --- Places and visits ------------------------------------------------------------------------

def _fill_place(p, data: PlaceIn):
    for field in ("name", "city", "country", "type", "michelin_stars", "notes", "lat", "lng"):
        setattr(p, field, getattr(data, field))


@router.post("/api/places", status_code=201)
def create_place(data: PlaceIn, session: Session = Depends(get_session)):
    _unique_name(session, Place, data.name, "place")
    p = Place()
    _fill_place(p, data)
    session.add(p)
    return {"id": _commit(session, p)}


@router.put("/api/places/{place_id}")
def update_place(place_id: int, data: PlaceIn, session: Session = Depends(get_session)):
    p = _get(session, Place, place_id, "Place")
    _unique_name(session, Place, data.name, "place", p.id)
    old = p.name
    _fill_place(p, data)
    pid = _commit(session, p)
    if p.name != old:
        photos.rename_place(old, p.name)  # its photos are named after it
    return {"id": pid}


@router.delete("/api/places/{place_id}")
def delete_place(place_id: int, session: Session = Depends(get_session)):
    p = _get(session, Place, place_id, "Place")
    n_t = session.query(TastingNote).filter_by(place_id=p.id).count()
    n_v = session.query(RestaurantVisit).filter_by(place_id=p.id).count()
    _refuse_if(n_t or n_v, f"{p.name} is used by {n_t} tasting note{'s' * (n_t != 1)} and {n_v} visit{'s' * (n_v != 1)}")
    session.delete(p)
    session.commit()
    return {"deleted": place_id}


def _fill_visit(session, v, data: VisitIn):
    v.place = _place(session, data.place)
    v.date, v.notes = data.date, data.notes


@router.post("/api/visits", status_code=201)
def create_visit(data: VisitIn, session: Session = Depends(get_session)):
    v = RestaurantVisit()
    _fill_visit(session, v, data)
    session.add(v)
    return {"id": _commit(session, v), "place_id": v.place_id}


@router.put("/api/visits/{visit_id}")
def update_visit(visit_id: int, data: VisitIn, session: Session = Depends(get_session)):
    v = _get(session, RestaurantVisit, visit_id, "Visit")
    _fill_visit(session, v, data)
    return {"id": _commit(session, v), "place_id": v.place_id}


@router.delete("/api/visits/{visit_id}")
def delete_visit(visit_id: int, session: Session = Depends(get_session)):
    v = _get(session, RestaurantVisit, visit_id, "Visit")
    place_id = v.place_id
    session.delete(v)
    session.commit()
    return {"deleted": visit_id, "place_id": place_id}


# --- Form prefill -----------------------------------------------------------------------------

def _ref(row, name=None):
    return {"id": row.id, "name": name or row.name} if row else None


def _stock(session, wine_ids):
    rows = (session.query(Bottle.wine_id, func.sum(Bottle.qty)).filter(Bottle.wine_id.in_(wine_ids), Bottle.qty > 0)
            .group_by(Bottle.wine_id).all())
    return {wid: int(n) for wid, n in rows}


def wine_summary(w, stock=0):
    return {
        "id": w.id, "producer_id": w.producer_id, "producer": w.producer.name if w.producer else "",
        "cuvee": w.cuvee or "", "vintage": w.vintage, "disgorgement_date": w.disgorgement_date, "type": w.type,
        "appellation": w.appellation.name if w.appellation else None, "appellation_id": w.appellation_id,
        "varietal": w.varietal.name if w.varietal else None, "varietal_id": w.varietal_id,
        "region": w.region_obj.name if w.region_obj else None, "stock": stock,
    }


def bottle_option(b):
    w = b.wine
    return {
        "id": b.id, "wine_id": b.wine_id, "qty": b.qty or 0, "bottle_size": b.bottle_size, "location": b.location,
        "label": f"{w.producer.name if w.producer else '?'} - {w.cuvee or ''} ({w.vintage or 'NV'}) - {b.bottle_size}" + (f" @ {b.location}" if b.location else ""),
        "wine": wine_summary(w),
    }


def _bottle_details(b):
    return {"bottle_size": b.bottle_size, "price": b.price, "currency": b.currency, "vendor": b.vendor,
            "provenance": b.provenance, "purchase_date": b.purchase_date}


def _place_out(p):
    return {"id": p.id, "name": p.name, "city": p.city, "country": p.country, "type": p.type} if p else None


@router.get("/api/forms/producers/{producer_id}")
def producer_form(producer_id: int, session: Session = Depends(get_session)):
    p = _get(session, Producer, producer_id, "Producer")
    out = {c: getattr(p, c) for c in ("id", "name", "subregion", "village", "winemaker", "owner", "type", "importers",
                                         "lists", "profile_url", "website", "notes", "description", "aliases")}
    out["region"] = _ref(p.region_obj)
    out["wines"] = session.query(Wine).filter_by(producer_id=p.id).count()
    return out


@router.get("/api/forms/appellations/{appellation_id}")
def appellation_form(appellation_id: int, session: Session = Depends(get_session)):
    a = _get(session, Appellation, appellation_id, "Appellation")
    out = {"id": a.id, **{c: getattr(a, c) for c in APPELLATION_FIELDS}}
    out["region"] = _ref(a.region_obj)
    out["wines"] = session.query(Wine).filter_by(appellation_id=a.id).count()
    return out


@router.get("/api/forms/vineyards/{vineyard_id}")
def vineyard_form(vineyard_id: int, session: Session = Depends(get_session)):
    v = _get(session, Vineyard, vineyard_id, "Vineyard")
    return {"id": v.id, "name": v.name, "region": _ref(v.region_obj), "sub_region": v.sub_region, "village": v.village,
            "wines": session.query(Wine).filter_by(vineyard_id=v.id).count()}


@router.get("/api/forms/wines/{wine_id}")
def wine_form(wine_id: int, session: Session = Depends(get_session)):
    w = _get(session, Wine, wine_id, "Wine")
    out = {c: getattr(w, c) for c in ("id", "cuvee", "vintage", "type", "disgorgement_date", "blend", "lwin",
                                         "drink_window_start", "drink_window_end")}
    out["grapes"] = [{"varietal": _ref(g.varietal), "share": g.share} for g in w.grapes]
    out.update(
        producer=_ref(w.producer), region=_ref(w.region_obj), appellation=_ref(w.appellation),
        varietal=_ref(w.varietal), vineyard=_ref(w.vineyard, vineyard_label(w.vineyard) if w.vineyard else None),
        summary=wine_summary(w, _stock(session, [w.id]).get(w.id, 0)),
        bottles=session.query(Bottle).filter_by(wine_id=w.id).count(),
    )
    return out


@router.get("/api/forms/bottles/{bottle_id}")
def bottle_form(bottle_id: int, session: Session = Depends(get_session)):
    b = _get(session, Bottle, bottle_id, "Bottle")
    return {
        "id": b.id, **_bottle_details(b), "qty": b.qty, "location": b.location, "last_price": b.last_price,
        "last_price_date": b.last_price_date, "last_price_source": b.last_price_source,
        "option": bottle_option(b), "wine": wine_summary(b.wine, _stock(session, [b.wine_id]).get(b.wine_id, 0)),
        "tastings": session.query(TastingNote).filter_by(bottle_id=b.id).count(),
    }


@router.get("/api/forms/tastings/{tasting_id}")
def tasting_form(tasting_id: int, session: Session = Depends(get_session)):
    tn = _get(session, TastingNote, tasting_id, "Tasting note")
    b = tn.bottle
    return {
        "id": tn.id, "date": tn.date, "rating": tn.rating, "glasses": tn.glasses, "sequence": tn.sequence,
        "tags": tn.tags, "notes": tn.notes, "place": _place_out(tn.place), "styles": [s.tag for s in tn.styles],
        "source": "other" if _is_adhoc(b) else "cellar",
        "bottle_id": b.id, "bottle": _bottle_details(b), "wine": wine_summary(b.wine),
    }


@router.get("/api/forms/places/{place_id}")
def place_form(place_id: int, session: Session = Depends(get_session)):
    p = _get(session, Place, place_id, "Place")
    return {
        **{c: getattr(p, c) for c in ("id", "name", "city", "country", "type", "michelin_stars", "notes", "lat", "lng")},
        "tastings": session.query(TastingNote).filter_by(place_id=p.id).count(),
        "visits": session.query(RestaurantVisit).filter_by(place_id=p.id).count(),
    }


@router.get("/api/forms/visits/{visit_id}")
def visit_form(visit_id: int, session: Session = Depends(get_session)):
    v = _get(session, RestaurantVisit, visit_id, "Visit")
    return {"id": v.id, "date": v.date, "notes": v.notes, "place": _place_out(v.place)}


# --- Lookups (type-ahead) ---------------------------------------------------------------------

@router.get("/api/lookups/options")
def lookup_options(session: Session = Depends(get_session)):
    place_types = [t for t, in session.query(Place.type).filter(Place.type.isnot(None)).group_by(Place.type)
                   .order_by(func.count().desc()).limit(40)]
    in_use = {loc for loc, in session.query(Bottle.location).filter(Bottle.qty > 0, Bottle.location.isnot(None))}
    groups = {g.name for g in settings.current.storage_groups}  # a group's name is its overflow spot
    locations = sorted(in_use | groups, key=location_sort_key)
    return {
        "wine_types": WINE_TYPES, "bottle_sizes": BOTTLE_SIZES, "currencies": currencies(), "blend_styles": BLEND_STYLES,
        "producer_types": PRODUCER_TYPES, "place_types": list(dict.fromkeys(PLACE_TYPES + place_types)),
        "locations": locations, "ad_hoc": AD_HOC,
        "regions": [{"id": r.id, "name": r.name, "country": r.country, "color": r.color}
                    for r in session.query(Region).order_by(Region.name)],
    }


@router.get("/api/lookups/producers")
def lookup_producers(q: str = "", limit: int = Query(LOOKUP_LIMIT, le=100), session: Session = Depends(get_session)):
    rows = session.query(Producer.id, Producer.name, Producer.region_id, Region.name.label("region"), Producer.aliases) \
        .outerjoin(Region, Producer.region_id == Region.id).order_by(Producer.name).all()
    # found by its other names too ("Chave" finds Jean-Louis Chave)
    return [{"id": r.id, "name": r.name, "region_id": r.region_id, "region": r.region}
            for r in search(rows, q, lambda r: (r.name, r.region, r.aliases), limit)]


@router.get("/api/lookups/appellations")
def lookup_appellations(q: str = "", region_id: int | None = None, limit: int = Query(LOOKUP_LIMIT, le=100),
                        session: Session = Depends(get_session)):
    rows = session.query(Appellation.id, Appellation.name, Appellation.region_id, Region.name.label("region"),
                         Appellation.aliases) \
        .outerjoin(Region, Appellation.region_id == Region.id).order_by(Appellation.name).all()
    if region_id:  # the wine's region first
        rows.sort(key=lambda r: r.region_id != region_id)
    # found by its other names too ("Ermitage" finds Hermitage)
    return [{"id": r.id, "name": r.name, "region": r.region, "region_id": r.region_id}
            for r in search(rows, q, lambda r: (r.name, r.region, r.aliases), limit)]


@router.get("/api/lookups/varietals")
def lookup_varietals(q: str = "", limit: int = Query(LOOKUP_LIMIT, le=200), session: Session = Depends(get_session)):
    rows = session.query(Varietal.id, Varietal.name, Varietal.aliases).order_by(Varietal.name).all()
    # found by an alias too ("Shiraz" finds Syrah): which one, for the picker's hint
    return [{"id": r.id, "name": r.name, "alias": matched_alias(q, r.name, r.aliases)}
            for r in search(rows, q, lambda r: (r.name, r.aliases), limit)]


def matched_alias(q, name, aliases):
    """The alias a query found a row by, when its name alone doesn't match ("Shiraz" for Syrah); else None."""
    words = fold(q).split()
    if not words or all(w in fold(name) for w in words):
        return None
    return next((a.strip() for a in (aliases or "").split(",") if a.strip() and all(w in fold(a) for w in words)), None)


@router.get("/api/lookups/vineyards")
def lookup_vineyards(q: str = "", region_id: int | None = None, limit: int = Query(LOOKUP_LIMIT, le=100),
                     session: Session = Depends(get_session)):
    query = session.query(Vineyard)
    if region_id:
        query = query.filter(Vineyard.region_id == region_id)
    rows = query.order_by(Vineyard.sub_region, Vineyard.village, Vineyard.name).all()
    out = [{"id": v.id, "name": vineyard_label(v)} for v in search(rows, q, lambda v: (v.name, v.village, v.sub_region), limit)]
    # the cadastre's lieux-dits too (the map store), those not already a vineyard: made one when the wine is saved
    import lieux_dits
    taken = {b for b, in session.query(Vineyard.boundary).filter(Vineyard.boundary.like("lieu_dit:%"))}
    hits = [h for h in lieux_dits.search(q) if f"lieu_dit:{h[0]}" not in taken] if len(q.strip()) >= 3 else []
    return out + [{"id": -(i + 1), "name": f"{name} · {d.get('commune_name') or '?'} (lieu-dit)", "ref": f"lieu_dit:{sid}"}
                  for i, (sid, name, d) in enumerate(hits)]


@router.get("/api/lookups/lieux-dits")
def lookup_lieux_dits(q: str = "", limit: int = Query(LOOKUP_LIMIT, le=50), session: Session = Depends(get_session)):
    """The cadastre's lieux-dits (the map store) whose name has every word of q (3 letters at least), the most in vines
    first: to make one a wine's vineyard, or a vineyard's outline. `mine`: the vineyard it is already, if any."""
    import lieux_dits
    from crus import cru_case
    if len(q.strip()) < 3:
        return []
    mine = dict(session.query(Vineyard.boundary, Vineyard.id).filter(Vineyard.boundary.like("lieu_dit:%")).all())
    return [{"id": i + 1, "name": cru_case(name), "ref": f"lieu_dit:{sid}", "village": d.get("commune_name"),
             "aocs": [a for a in (d.get("aocs") or "").split("; ") if a], "vines": d.get("vines"),
             "mine": mine.get(f"lieu_dit:{sid}")}
            for i, (sid, name, d) in enumerate(lieux_dits.search(q, limit))]


@router.get("/api/lookups/places")
def lookup_places(q: str = "", limit: int = Query(LOOKUP_LIMIT, le=100), session: Session = Depends(get_session)):
    rows = session.query(Place.id, Place.name, Place.city, Place.country, Place.type).order_by(Place.name).all()
    return [r._asdict() for r in search(rows, q, lambda r: (r.name, r.city, r.country), limit)]


@router.get("/api/lookups/map-link")
def map_link(url: str):
    """Coordinates (and the place's name, when the link has one) behind a Google Maps link, short ones included."""
    try:
        return maplinks.resolve(url)
    except maplinks.LinkError as e:
        raise HTTPException(422, str(e))


@router.get("/api/lookups/next-sequence")
def next_sequence(date: Date, place_id: int, session: Session = Depends(get_session)):
    """Where a new note falls in that evening's line-up: after the highest order logged at that place that day
    (notes without an order still count)."""
    count, highest = (session.query(func.count(TastingNote.id), func.max(TastingNote.sequence))
                      .filter(TastingNote.date == date, TastingNote.place_id == place_id).one())
    return {"next": max(highest or 0, count) + 1, "count": count}


@router.get("/api/lookups/wines")
def lookup_wines(q: str = "", producer_id: int | None = None, limit: int = Query(30, le=100),
                 session: Session = Depends(get_session)):
    """Type-ahead over every wine by producer, cuvée, appellation, vintage (e.g. "coulaine chinon 2020")."""
    if not producer_id and not q.strip():
        return []
    query = (session.query(Wine.id, Producer.name, Wine.cuvee, Appellation.name, Wine.vintage, Varietal.name, Region.name)
             .join(Producer, Wine.producer_id == Producer.id)
             .outerjoin(Appellation, Wine.appellation_id == Appellation.id)
             .outerjoin(Varietal, Wine.varietal_id == Varietal.id)
             .outerjoin(Region, Wine.region_id == Region.id))
    if producer_id:
        query = query.filter(Wine.producer_id == producer_id)
    # Producer, cuvée, appellation, then newest vintage first
    rows = sorted(query.all(), key=lambda r: (fold(r[1]), fold(r[2]), r[3] or "", -int(r[4]) if (r[4] or "").isdigit() else 0))
    ids = [r[0] for r in search(rows, q, lambda r: r[1:], limit)]
    wines = {w.id: w for w in session.query(Wine).filter(Wine.id.in_(ids)).options(
        joinedload(Wine.producer), joinedload(Wine.appellation), joinedload(Wine.varietal), joinedload(Wine.region_obj))}
    stock = _stock(session, ids)
    return [wine_summary(wines[i], stock.get(i, 0)) for i in ids]


@router.get("/api/lookups/bottles")
def lookup_bottles(q: str = "", wine_id: int | None = None, limit: int = Query(LOOKUP_LIMIT, le=100),
                   session: Session = Depends(get_session)):
    """Bottles in stock, to pick the one a tasting note is about."""
    query = session.query(Bottle).join(Wine).join(Producer).filter(Bottle.qty > 0) \
        .options(joinedload(Bottle.wine).joinedload(Wine.producer), joinedload(Bottle.wine).joinedload(Wine.appellation),
                 joinedload(Bottle.wine).joinedload(Wine.varietal), joinedload(Bottle.wine).joinedload(Wine.region_obj))
    if wine_id:
        query = query.filter(Bottle.wine_id == wine_id)
    rows = query.order_by(Producer.name, Wine.cuvee, Wine.vintage).all()
    return [bottle_option(b) for b in search(rows, q, lambda b: (
        b.wine.producer.name, b.wine.cuvee, b.wine.appellation.name if b.wine.appellation else "", b.wine.vintage, b.location), limit)]
