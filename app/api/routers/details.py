"""Detail pages: regions, grapes, vintages, producers, wines, bottles, places, appellations and vineyards, with their maps.

`GET /api/appellations/{id}` and `GET /api/vineyards/{id}` also feed the map's side panel: keep their fields.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session, joinedload

from routers.lists import family as list_family, marks as list_marks
from routers.map import MAPPABLE_VINE, map_stats, shapes_response
from cellar import load_cellar, location_group, maturity, to_base
from display import iso, vineyard_label, vintage_label
from photos import photo_index, photo_url
import geo
import grapes
import plugins
import scores
import wiki
from db import same, Appellation, Bottle, Place, Producer, Region, RestaurantVisit, TastingNote, Varietal, Vineyard, Wine, WineGrape, get_session, same_cuvee

router = APIRouter()


def _region(obj):
    r = obj.region_obj
    return {"region": r.name if r else None, "region_color": r.color if r else None}


def _get(session, model, id_, what, *options):
    obj = session.query(model).options(*options).filter(model.id == id_).one_or_none()
    if obj is None:
        raise HTTPException(404, f"{what} not found")
    return obj


def cellar_lines(session, key, ids):
    """Stocked bottle lines (same rows as GET /api/cellar) whose `key` is in ids."""
    bottles, _ = load_cellar(session)
    ids = set(ids)
    return [b for b in bottles if b[key] in ids]


def _cellar_totals(lines):
    return {"bottles": sum(b["qty"] for b in lines), "value": round(sum(b["qty"] * b["market_base"] for b in lines))}


def tastings(session, *filters):
    """Tasting notes (newest first) with their wine and place, flattened for the history cards."""
    rows = (
        session.query(TastingNote)
        .join(TastingNote.bottle).join(Bottle.wine)
        .options(
            joinedload(TastingNote.place),
            joinedload(TastingNote.bottle).joinedload(Bottle.wine).options(
                joinedload(Wine.producer), joinedload(Wine.appellation), joinedload(Wine.region_obj)),
        )
        .filter(*filters)
        .order_by(TastingNote.date.desc(), TastingNote.sequence)
        .all()
    )
    out = []
    index = photo_index()
    for t in rows:
        b, w, p = t.bottle, t.bottle.wine, t.place
        out.append({
            "id": t.id, "date": iso(t.date), "rating": t.rating, "notes": t.notes or None, "glasses": t.glasses,
            "place": {"id": p.id, "name": p.name, "city": p.city, "country": p.country, "type": p.type,
                      "michelin_stars": p.michelin_stars} if p else None,
            "location": t.location, "photo": photo_url(index, p.name if p else t.location, t.date),
            "bottle_id": b.id, "format": b.bottle_size, "price_base": round(to_base(b.price, b.currency), 2),
            "wine_id": w.id, "producer_id": w.producer_id, "producer": w.producer.name, "cuvee": w.cuvee or "",
            "appellation": w.appellation.name if w.appellation else None, "vintage": vintage_label(w.vintage, w.disgorgement_date),
            "color": w.type, "score": scores.preferred_score(w.scores), "scores": scores.label(w.scores), **_region(w),
        })
    return out


def _wine_counts(session, wine_ids):
    """{wine_id: bottles in cellar}, {wine_id: tasting notes}."""
    if not wine_ids:
        return {}, {}
    bottles = dict(session.query(Bottle.wine_id, func.sum(Bottle.qty))
                   .filter(Bottle.wine_id.in_(wine_ids), Bottle.qty > 0).group_by(Bottle.wine_id).all())
    tasted = dict(session.query(Bottle.wine_id, func.count(TastingNote.id)).join(TastingNote.bottle)
                  .filter(Bottle.wine_id.in_(wine_ids)).group_by(Bottle.wine_id).all())
    return bottles, tasted


def _vintage_sort_key(v):
    return (v["vintage"][:2] != "NV", v["vintage"])


def wine_catalog(session, wines):
    """Wines grouped by cuvée (same cuvée, appellation and grape), each with its vintages."""
    bottles, tasted = _wine_counts(session, [w.id for w in wines])
    on_lists, cuvee_lists = list_marks(session, wines)
    families = {}
    for w in wines:
        key = (w.cuvee or "", w.appellation_id, w.varietal_id)
        fam = families.setdefault(key, {
            "cuvee": w.cuvee or "", "producer_id": w.producer_id, "producer": w.producer.name,
            "appellation": {"id": w.appellation.id, "name": w.appellation.name} if w.appellation else None,
            "varietal": w.varietal.name if w.varietal else None, "color": w.type, "vintages": [],
            "lists": [],  # lists naming the cuvée, any vintage
        })
        for name in cuvee_lists.get(list_family(w), []):
            if name not in fam["lists"]:
                fam["lists"].append(name)
        fam["vintages"].append({"id": w.id, "vintage": vintage_label(w.vintage, w.disgorgement_date), "bottles": bottles.get(w.id, 0),
                                "tastings": tasted.get(w.id, 0), "score": scores.preferred_score(w.scores),
                                "scores": scores.label(w.scores), "lists": on_lists.get(w.id, [])})
    for fam in families.values():
        fam["vintages"].sort(key=_vintage_sort_key, reverse=True)
    return sorted(families.values(), key=lambda f: (f["producer"].lower(), f["cuvee"].lower()))


def _catalog_query(session):
    return session.query(Wine).options(
        joinedload(Wine.producer), joinedload(Wine.appellation), joinedload(Wine.varietal))


def _ref(obj):
    return {"id": obj.id, "name": obj.name} if obj else None


# --- Producers -------------------------------------------------------------------------------------------

def _places_of(session, wines):
    """([appellations], [vineyards]) the wines come from, each with its wines, bottles in the cellar and tastings,
    most tasted first."""
    bottles, tasted = _wine_counts(session, [w.id for w in wines])
    apps, vines = {}, {}
    for w in wines:
        counts = {"wines": 1, "bottles": int(bottles.get(w.id) or 0), "tastings": tasted.get(w.id, 0)}
        for obj, out, extra in ((w.appellation, apps, {}),
                                (w.vineyard, vines, {"village": w.vineyard and w.vineyard.village,
                                                     "subregion": w.vineyard and w.vineyard.sub_region})):
            if obj is None:
                continue
            row = out.setdefault(obj.id, {"id": obj.id, "name": obj.name, **extra, "wines": 0, "bottles": 0, "tastings": 0})
            for k, n in counts.items():
                row[k] += n
    order = lambda r: (-r["tastings"], -r["bottles"], -r["wines"], r["name"].lower())  # noqa: E731
    return sorted(apps.values(), key=order), sorted(vines.values(), key=order)


@router.get("/api/producers/{producer_id}")
def producer_detail(producer_id: int, session: Session = Depends(get_session)):
    p = _get(session, Producer, producer_id, "Producer", joinedload(Producer.region_obj))
    wines = _catalog_query(session).options(joinedload(Wine.vineyard)).filter(Wine.producer_id == producer_id).all()
    lines = cellar_lines(session, "producer_id", [producer_id])
    appellations, vineyards = _places_of(session, wines)
    history = tastings(session, Wine.producer_id == producer_id)
    lists = [x.strip(" '\"") for x in (p.lists or "").strip("[]").split(",") if x.strip(" '\"")]
    return {
        "id": p.id, "name": p.name, **_region(p), "subregion": p.subregion, "village": p.village,
        "winemaker": p.winemaker, "owner": p.owner, "type": p.type, "importers": p.importers,
        "description": p.description, "notes": p.notes, "website": p.website, "profile_url": p.profile_url,
        "aliases": p.aliases,
        "lists": lists,
        "stats": {**_cellar_totals(lines), "tastings": len(history), "wines": len(wines)},
        "wines": wine_catalog(session, wines),
        "appellations": appellations,
        "vineyards": vineyards,
        "cellar": lines,
        "tastings": history,
    }


# --- Wines and bottles -----------------------------------------------------------------------------------

@router.get("/api/wines/{wine_id}")
def wine_detail(wine_id: int, session: Session = Depends(get_session)):
    w = _get(session, Wine, wine_id, "Wine", joinedload(Wine.producer), joinedload(Wine.appellation),
             joinedload(Wine.vineyard), joinedload(Wine.varietal), joinedload(Wine.region_obj))
    # Every vintage of the same cuvée: same producer, cuvée, appellation and grape
    family = (
        session.query(Wine)
        .filter(Wine.producer_id == w.producer_id, same_cuvee(w.cuvee),
                same(Wine.appellation_id, w.appellation_id), same(Wine.varietal_id, w.varietal_id))
        .all()
    )
    ids = [x.id for x in family]
    bottles, tasted = _wine_counts(session, ids)
    on_lists, cuvee_lists = list_marks(session, family)
    vintages = sorted(
        ({"id": x.id, "vintage": vintage_label(x.vintage, x.disgorgement_date), "bottles": bottles.get(x.id, 0), "tastings": tasted.get(x.id, 0),
          "score": scores.preferred_score(x.scores), "scores": scores.label(x.scores), "lists": on_lists.get(x.id, [])}
         for x in family),
        key=_vintage_sort_key, reverse=True)
    v = w.vineyard
    return {
        "id": w.id, "producer": _ref(w.producer), "cuvee": w.cuvee or "", "vintage": vintage_label(w.vintage, w.disgorgement_date),
        "disgorgement_date": w.disgorgement_date, "color": w.type, **_region(w),
        "appellation": _ref(w.appellation),
        "vineyard": {"id": v.id, "name": v.name, "label": vineyard_label(v)} if v else None,
        "varietal": w.varietal.name if w.varietal else None, "blend": w.blend, "lwin": w.lwin,
        "grapes": grape_list(w),
        "drink_window": [w.drink_window_start, w.drink_window_end],
        "scores": scores.listing(w.scores),
        "actions": plugins.wine_actions(w),  # buttons the plug-ins add (plugins.py)
        "maturity": maturity(w.drink_window_start, w.drink_window_end),
        "vintages": vintages,
        # lists naming the cuvée, any vintage (those naming a vintage: on it)
        "cuvee_lists": cuvee_lists.get(list_family(w), []),
        "cellar": cellar_lines(session, "wine_id", ids),
        "tastings": tastings(session, Bottle.wine_id.in_(ids)),
    }


@router.get("/api/bottles/{bottle_id}")
def bottle_detail(bottle_id: int, session: Session = Depends(get_session)):
    b = _get(session, Bottle, bottle_id, "Bottle")
    change = ((b.last_price - b.price) / b.price * 100) if b.last_price and b.price else None
    return {
        "id": b.id, "wine_id": b.wine_id, "qty": b.qty, "bottle_size": b.bottle_size, "location": b.location,
        "location_group": location_group(b.location or ""),
        "price": b.price, "currency": b.currency, "price_base": round(to_base(b.price, b.currency), 2) if b.price else None,
        "last_price": b.last_price, "last_price_date": iso(b.last_price_date), "last_price_source": b.last_price_source,
        "change_pct": round(change, 1) if change is not None else None,
        "vendor": b.vendor, "provenance": b.provenance, "purchase_date": iso(b.purchase_date),
    }


# --- Places ----------------------------------------------------------------------------------------------

@router.get("/api/places/{place_id}")
def place_detail(place_id: int, session: Session = Depends(get_session)):
    p = _get(session, Place, place_id, "Place")
    history = tastings(session, TastingNote.place_id == place_id)
    visits = session.query(RestaurantVisit).filter_by(place_id=place_id).order_by(RestaurantVisit.date.desc()).all()
    # A visit is a day there: tastings and logged visits on the same day count once
    days = {t["date"] for t in history if t["date"]} | {iso(v.date) for v in visits if v.date}
    index = photo_index()
    return {
        "id": p.id, "name": p.name, "city": p.city, "country": p.country, "type": p.type,
        "michelin_stars": p.michelin_stars, "notes": p.notes, "lat": p.lat, "lng": p.lng,
        "stats": {"visits": len(days), "tastings": len(history),
                  "value": round(sum(t["price_base"] for t in history), 2)},
        "visits": [{"id": v.id, "date": iso(v.date), "notes": v.notes or None, "photo": photo_url(index, p.name, v.date)}
                   for v in visits],
        "tastings": history,
    }


# --- Appellations and vineyards --------------------------------------------------------------------------

def _producers(session, *filters):
    rows = (session.query(Producer.id, Producer.name, func.count(Wine.id)).join(Wine.producer)
            .filter(*filters).group_by(Producer.id, Producer.name).all())
    return sorted(({"id": i, "name": n, "wines": c} for i, n, c in rows), key=lambda p: p["name"].lower())


def _vineyards(session, *filters):
    """The vineyards of some wines, with how many of those wines each has."""
    rows = (session.query(Vineyard.id, Vineyard.name, Vineyard.village, func.count(Wine.id)).join(Wine.vineyard)
            .filter(*filters).group_by(Vineyard.id, Vineyard.name, Vineyard.village).all())
    return sorted(({"id": i, "name": n, "village": v, "wines": c} for i, n, v, c in rows), key=lambda x: x["name"].lower())


@router.get("/api/appellations/{appellation_id}")
def appellation_detail(appellation_id: int, session: Session = Depends(get_session)):
    a = _get(session, Appellation, appellation_id, "Appellation", joinedload(Appellation.region_obj))
    lines = cellar_lines(session, "appellation_id", [a.id])
    history = tastings(session, Wine.appellation_id == a.id)
    return {
        # Map side panel fields
        "id": a.id, "name": a.name, "region": a.region_obj.name if a.region_obj else None,
        "subregion": a.subregion, "type": a.type, "category": a.category, "pdo_id": a.pdo_id,
        "registration_date": iso(a.registration_date),
        "max_yield_hl": a.max_yield_hl, "max_yield_kg": a.max_yield_kg,
        "varieties": a.varieties_text, "details": a.details, "aliases": a.aliases,
        "bottles": _cellar_totals(lines)["bottles"],
        # Detail page
        "region_color": a.region_obj.color if a.region_obj else None,
        "colors": a.colors, "location_link": a.location_link, "full_outline": geo.has_detail(a.boundary),
        "stats": {**_cellar_totals(lines), "tastings": len(history)},
        "producers": _producers(session, Wine.appellation_id == a.id),
        "vineyards": _vineyards(session, Wine.appellation_id == a.id),
        "cellar": lines,
        "tastings": history,
    }


@router.get("/api/vineyards/{vineyard_id}")
def vineyard_detail(vineyard_id: int, session: Session = Depends(get_session)):
    v = _get(session, Vineyard, vineyard_id, "Vineyard", joinedload(Vineyard.region_obj))
    lines = cellar_lines(session, "vineyard_id", [v.id])
    history = tastings(session, Wine.vineyard_id == v.id)
    wines = _catalog_query(session).filter(Wine.vineyard_id == v.id).all()
    apps = {w.appellation.id: w.appellation.name for w in wines if w.appellation}
    return {
        # Map side panel fields
        "id": v.id, "name": v.name, "region": v.region_obj.name if v.region_obj else None,
        "subregion": v.sub_region, "village": v.village,
        "bottles": _cellar_totals(lines)["bottles"],
        # Detail page
        "region_color": v.region_obj.color if v.region_obj else None,
        "vineyard_id": v.vineyard_id, "full_outline": geo.has_detail(v.boundary),
        "appellations": [{"id": i, "name": n} for i, n in sorted(apps.items(), key=lambda x: x[1])],
        "stats": {**_cellar_totals(lines), "tastings": len(history)},
        "wines": wine_catalog(session, wines),
        "cellar": lines,
        "tastings": history,
    }


# --- Regions ---------------------------------------------------------------------------------------------

def _region_by_key(session, key):
    """A region by id, or by name (any case) so pages that only know the name can link to it."""
    r = session.get(Region, int(key)) if key.isdigit() else (
        session.query(Region).filter(func.lower(Region.name) == key.strip().lower()).first())
    if r is None:
        raise HTTPException(404, "Region not found")
    return r


@router.get("/api/regions/{key}")
def region_detail(key: str, session: Session = Depends(get_session)):
    """A wine region: its appellations and producers with your bottles and tastings, the cellar, the history."""
    r = _region_by_key(session, key)
    lines = [b for b in load_cellar(session)[0] if b["region"] == r.name]
    history = tastings(session, Wine.region_id == r.id)
    app_stats, _ = map_stats(session)

    apps = session.query(Appellation).filter(Appellation.region_id == r.id).all()
    appellations = sorted((
        {"id": a.id, "name": a.name, "subregion": a.subregion, "type": a.type,
         "bottles": app_stats.get(a.id, {}).get("bottles", 0), "tastings": app_stats.get(a.id, {}).get("tastings", 0)}
        for a in apps), key=lambda a: a["name"].lower())

    # Producers based in the region, plus any with wines from it
    wines_in = dict(session.query(Wine.producer_id, func.count(Wine.id)).filter(Wine.region_id == r.id)
                    .group_by(Wine.producer_id).all())
    producers = session.query(Producer).filter((Producer.region_id == r.id) | Producer.id.in_(list(wines_in))).all()
    bottles_by, tasted_by = {}, {}
    for b in lines:
        bottles_by[b["producer_id"]] = bottles_by.get(b["producer_id"], 0) + b["qty"]
    for t in history:
        tasted_by[t["producer_id"]] = tasted_by.get(t["producer_id"], 0) + 1
    producer_rows = sorted((
        {"id": p.id, "name": p.name, "subregion": p.subregion, "village": p.village, "wines": wines_in.get(p.id, 0),
         "bottles": bottles_by.get(p.id, 0), "tastings": tasted_by.get(p.id, 0)}
        for p in producers), key=lambda p: p["name"].lower())

    vineyards = session.query(func.count(Vineyard.id)).filter(Vineyard.region_id == r.id, MAPPABLE_VINE).scalar()
    return {
        "id": r.id, "name": r.name, "country": r.country, "color": r.color,
        "stats": {**_cellar_totals(lines), "tastings": len(history), "producers": len(producer_rows),
                  "appellations": len(appellations), "vineyards": vineyards},
        "appellations": appellations,
        "producers": producer_rows,
        "cellar": lines,
        "tastings": history,
    }


# --- Grapes ----------------------------------------------------------------------------------------------

def _grape_by_key(session, key):
    """A grape by id, or by name (any case) so pages that only know the name can link to it."""
    g = session.get(Varietal, int(key)) if key.isdigit() else (
        session.query(Varietal).filter(func.lower(Varietal.name) == key.strip().lower()).first())
    if g is None:
        raise HTTPException(404, "Grape not found")
    return g


def grape_list(w):
    """A wine's grapes for its page: [{"id", "name", "share"}], the main one first."""
    return [{"id": g.varietal_id, "name": g.varietal.name, "share": g.share} for g in w.grapes if g.varietal]


def _wines_with(grape_id):
    """The wines a grape is in, main grape or not."""
    return select(WineGrape.wine_id).where(WineGrape.varietal_id == grape_id)


@router.get("/api/grapes/{key}")
def grape_detail(key: str, session: Session = Depends(get_session)):
    """A grape: where its wines come from, its producers, the cellar and the history, plus its profile
    (climate, acidity, tannin, aromas...) and its family."""
    g = _grape_by_key(session, key)
    with_grape = {i for (i,) in session.execute(_wines_with(g.id))}
    lines = [b for b in load_cellar(session)[0] if b["wine_id"] in with_grape]
    history = tastings(session, Wine.id.in_(_wines_with(g.id)))

    def tally(rows, key, n):
        out = {}
        for r in rows:
            out[r[key]] = out.get(r[key], 0) + n(r)
        return out
    bottles_by_region, tasted_by_region = tally(lines, "region", lambda b: b["qty"]), tally(history, "region", lambda t: 1)
    bottles_by_producer, tasted_by_producer = tally(lines, "producer_id", lambda b: b["qty"]), tally(history, "producer_id", lambda t: 1)

    wines_by_region = dict(session.query(Region.name, func.count(Wine.id)).join(Wine.region_obj)
                           .filter(Wine.id.in_(_wines_with(g.id))).group_by(Region.name).all())
    colors = dict(session.query(Region.name, Region.color).all())
    regions = sorted((
        {"name": name, "color": colors.get(name), "wines": wines_by_region.get(name, 0),
         "bottles": bottles_by_region.get(name, 0), "tastings": tasted_by_region.get(name, 0)}
        for name in set(wines_by_region) | {r for r in bottles_by_region if r != "Unknown"} | {r for r in tasted_by_region if r}
    ), key=lambda r: (-(r["bottles"] + r["tastings"]), -r["wines"], r["name"]))

    producer_rows = (session.query(Producer.id, Producer.name, Region.name, func.count(Wine.id))
                     .join(Wine, Wine.producer_id == Producer.id).outerjoin(Region, Producer.region_id == Region.id)
                     .filter(Wine.id.in_(_wines_with(g.id))).group_by(Producer.id, Producer.name, Region.name).all())
    producers = sorted((
        {"id": i, "name": n, "region": rn, "wines": c,
         "bottles": bottles_by_producer.get(i, 0), "tastings": tasted_by_producer.get(i, 0)}
        for i, n, rn, c in producer_rows), key=lambda p: p["name"].lower())

    prof = grapes.profile(g)
    import grape_family
    return {
        "id": g.id, "name": g.name, "aliases": g.aliases,
        "color": g.color, "origin": g.origin,
        "vivc": {"number": g.vivc, "url": grape_family.VIVC_PAGE.format(g.vivc)} if g.vivc else None,
        "family": grape_family.families(session).family(g.id),
        "profile": prof,
        "stats": {**_cellar_totals(lines), "tastings": len(history), "producers": len(producers),
                  "regions": len(regions), "wines": sum(wines_by_region.values())},
        "regions": regions,
        "producers": producers,
        "cellar": lines,
        "tastings": history,
    }


# --- Vintages --------------------------------------------------------------------------------------------

def _vintage_filter(year):
    """Wines of a vintage: "2016", or "NV" (no vintage recorded counts as NV)."""
    if year.upper() == "NV":
        return (Wine.vintage.is_(None)) | (Wine.vintage.in_(["", "NV", "nv"]))
    return Wine.vintage == year


@router.get("/api/vintages")
def vintages(session: Session = Depends(get_session)):
    """Every vintage with its wines, bottles in the cellar and tastings, newest first (NV last); `regions` splits
    the bottles and tastings by region (biggest first), for the bars in the regions' colors."""
    rows = session.query(Wine.id, Wine.vintage, Region.name).outerjoin(Region, Wine.region_id == Region.id).all()
    year_of = {i: (v if v and v.strip().isdigit() else "NV") for i, v, _ in rows}
    region_of = {i: r for i, _, r in rows}
    bottles, tasted = _wine_counts(session, list(year_of))
    out = {}
    for i, y in year_of.items():
        r = out.setdefault(y, {"vintage": y, "wines": 0, "bottles": 0, "tastings": 0, "regions": {}})
        b, t = int(bottles.get(i) or 0), tasted.get(i, 0)
        r["wines"] += 1
        r["bottles"] += b
        r["tastings"] += t
        if b or t:
            g = r["regions"].setdefault(region_of[i], {"region": region_of[i], "bottles": 0, "tastings": 0})
            g["bottles"] += b
            g["tastings"] += t
    for r in out.values():
        r["regions"] = sorted(r["regions"].values(), key=lambda g: -(g["bottles"] + g["tastings"]))
    return sorted(out.values(), key=lambda r: (r["vintage"] != "NV", r["vintage"]), reverse=True)


@router.get("/api/vintages/{year}")
def vintage_detail(year: str, session: Session = Depends(get_session)):
    """A vintage: its wines by region, the best rated, the cellar and the history, and the vintages either side."""
    year = year.strip()
    if not (year.isdigit() and len(year) == 4) and year.upper() != "NV":
        raise HTTPException(404, "Vintage not found")
    year = "NV" if year.upper() == "NV" else year
    wines = _catalog_query(session).options(joinedload(Wine.region_obj)).filter(_vintage_filter(year)).all()
    if not wines:
        raise HTTPException(404, "Vintage not found")
    ids = {w.id for w in wines}
    lines = [b for b in load_cellar(session)[0] if b["wine_id"] in ids]
    history = tastings(session, _vintage_filter(year))
    bottles, tasted = _wine_counts(session, list(ids))

    regions = {}
    for w in wines:
        r = w.region_obj
        row = regions.setdefault(r.name if r else "Unknown", {"name": r.name if r else "Unknown",
                                                               "color": r.color if r else None,
                                                               "wines": 0, "bottles": 0, "tastings": 0})
        row["wines"] += 1
        row["bottles"] += int(bottles.get(w.id) or 0)
        row["tastings"] += tasted.get(w.id, 0)

    # Ranked by the preferred critic's score (Settings)
    graded = [(scores.number(s), s, w) for w in wines if (s := scores.preferred_score(w.scores)) and scores.number(s)]
    scored = sorted(((n, w) for n, _, w in graded), key=lambda x: (-x[0], x[1].producer.name.lower()))
    by_wine = {w.id: s for _, s, w in graded}
    best = [{"id": w.id, "producer": w.producer.name, "cuvee": w.cuvee or "",
             "appellation": w.appellation.name if w.appellation else None, "color": w.type, "score": by_wine[w.id],
             "scores": scores.label(w.scores),
             "bottles": int(bottles.get(w.id) or 0), "tastings": tasted.get(w.id, 0)} for _, w in scored]

    years = sorted({v for (v,) in session.query(Wine.vintage).distinct() if v and v.strip().isdigit()})
    prev_ = next_ = None
    if year != "NV" and year in years:
        i = years.index(year)
        prev_, next_ = (years[i - 1] if i else None), (years[i + 1] if i + 1 < len(years) else None)
    mine = [s for s, w in scored if bottles.get(w.id) or tasted.get(w.id)]
    return {
        "vintage": year, "prev": prev_, "next": next_,
        "stats": {**_cellar_totals(lines), "tastings": len(history), "wines": len(wines),
                  "producers": len({w.producer_id for w in wines}), "regions": len(regions),
                  "critic": scores.preferred(),
                  "score_mine": round(sum(mine) / len(mine), 1) if mine else None, "score_count": len(scored)},
        "regions": sorted(regions.values(), key=lambda r: (-(r["bottles"] + r["tastings"]), -r["wines"], r["name"])),
        "best": best[:50],
        "wines": wine_catalog(session, wines),
        "cellar": lines,
        "tastings": history,
    }


# --- About (Wikipedia) -----------------------------------------------------------------------------------

@router.get("/api/grapes/{key}/about")
def grape_about(key: str, session: Session = Depends(get_session)):
    """A description and a photo of the grape, from Wikipedia (cached; separate so pages don't wait)."""
    return wiki.about("grape", _grape_by_key(session, key).name)


# --- Map shapes ------------------------------------------------------------------------------------------

def shapes(session, app_ids, vine_ids):
    """Appellation and vineyard shapes as two GeoJSON collections."""
    return shapes_response(session, app_ids, vine_ids)


def _wine_places(session, *filters):
    rows = session.query(Wine.appellation_id, Wine.vineyard_id).filter(*filters).distinct().all()
    return {a for a, _ in rows if a}, {v for _, v in rows if v}


@router.get("/api/producers/{producer_id}/shapes")
def producer_shapes(producer_id: int, session: Session = Depends(get_session)):
    """Where the producer's wines come from."""
    _get(session, Producer, producer_id, "Producer")
    return shapes(session, *_wine_places(session, Wine.producer_id == producer_id))


@router.get("/api/wines/{wine_id}/shapes")
def wine_shapes(wine_id: int, session: Session = Depends(get_session)):
    w = _get(session, Wine, wine_id, "Wine")
    return shapes(session, [w.appellation_id] if w.appellation_id else [], [w.vineyard_id] if w.vineyard_id else [])


@router.get("/api/appellations/{appellation_id}/shapes")
def appellation_shapes(appellation_id: int, session: Session = Depends(get_session)):
    """The appellation, with the vineyards of its wines."""
    _get(session, Appellation, appellation_id, "Appellation")
    _, vine_ids = _wine_places(session, Wine.appellation_id == appellation_id)
    return shapes(session, [appellation_id], vine_ids)


@router.get("/api/regions/{key}/shapes")
def region_shapes(key: str, top: str = "", limit: int = 8, session: Session = Depends(get_session)):
    """The region's outline, with the appellations and vineyards you hold bottles from or have tasted
    (a region holds hundreds: the rest are on the map page). With top=tastings or top=bottles, only the
    `limit` appellations you've tasted / hold the most (the region page's list), no vineyards."""
    r = _region_by_key(session, key)
    app_stats, vine_stats = map_stats(session)
    in_region_apps = {i for (i,) in session.query(Appellation.id).filter(Appellation.region_id == r.id)}
    if top in ("tastings", "bottles"):
        ranked = sorted((k for k, s in app_stats.items() if k in in_region_apps and s.get(top)),
                        key=lambda k: -app_stats[k][top])
        return shapes_response(session, ranked[:max(0, limit)], [], region=r)
    in_region_vines = {i for (i,) in session.query(Vineyard.id).filter(Vineyard.region_id == r.id)}
    mine = lambda stats, ids: [k for k, s in stats.items() if k in ids and (s.get("bottles") or s.get("tastings"))]  # noqa: E731
    return shapes_response(session, mine(app_stats, in_region_apps), mine(vine_stats, in_region_vines), region=r)


@router.get("/api/vineyards/{vineyard_id}/shapes")
def vineyard_shapes(vineyard_id: int, session: Session = Depends(get_session)):
    """The vineyard, inside the appellations of its wines."""
    _get(session, Vineyard, vineyard_id, "Vineyard")
    app_ids, _ = _wine_places(session, Wine.vineyard_id == vineyard_id)
    return shapes(session, app_ids, [vineyard_id])
