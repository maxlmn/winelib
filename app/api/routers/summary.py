"""Summary dashboard: tasting history and cellar inventory."""
from collections import Counter, defaultdict
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text, union
from sqlalchemy.orm import Session

from cellar import load_cellar
from db import Place, Region, RestaurantVisit, TastingNote, get_session

router = APIRouter()

FALLBACK_COLOR = "#9a9893"
TOP = 25  # producers and appellations: the page shows 5, the rest on demand
TOP_GRAPES = 15  # the rest are summed into one "Other grapes" bar
HIGHLIGHTS = 5  # wines or places in each highlight card

TASTINGS_SQL = text("""
    SELECT w.id AS wine_id, w.type AS color, r.name AS region, p.id AS producer_id, p.name AS producer,
           a.id AS appellation_id, a.name AS appellation, v.name AS varietal, w.vintage, w.cuvee, t.rating,
           t.id AS tasting_id, t.date, t.sequence, t.place_id, pl.name AS place, t.location, b.bottle_size AS format
    FROM tasting_notes t
    JOIN cellar b ON t.bottle_id = b.id
    LEFT JOIN places pl ON t.place_id = pl.id
    JOIN wines w ON b.wine_id = w.id
    JOIN producers p ON w.producer_id = p.id
    LEFT JOIN regions r ON w.region_id = r.id
    LEFT JOIN appellations a ON w.appellation_id = a.id
    LEFT JOIN varietals v ON w.varietal_id = v.id
""")


def vintage_key(v):
    # Years in order, then NV; anything else first
    if v == "NV":
        return 9999
    try:
        return int(v)
    except ValueError:
        return 0


class Tally:
    """Weighted counts of rows (tastings or bottles) by color, region, producer, appellation, grape and vintage."""

    def __init__(self, colors):
        self.colors = colors
        self.total = 0
        self.by = defaultdict(Counter)
        self.names = {}
        self.home = defaultdict(Counter)  # producer / appellation -> region weights, to color their bars
        self.grape_types = defaultdict(Counter)  # grape -> wine colors (Red, White...), to color its bar
        self.vintage_regions = defaultdict(Counter)  # vintage -> region weights, to stack its column

    def add(self, row, weight=1):
        region = row["region"] or "Unknown"
        self.total += weight
        if row["color"]:
            self.by["color"][row["color"]] += weight
        self.by["region"][region] += weight
        vintage = (row["vintage"] or "NV").split(" - ")[0]
        self.by["vintage"][vintage] += weight
        self.vintage_regions[vintage][region] += weight
        if row["varietal"]:
            self.by["grape"][row["varietal"]] += weight
            if row["color"]:
                self.grape_types[row["varietal"]][row["color"]] += weight
        for kind in ("producer", "appellation"):
            key = row[f"{kind}_id"]
            if key:
                self.by[kind][key] += weight
                self.names[kind, key] = row[kind]
                self.home[kind, key][region] += weight

    def counts(self, kind):
        return [{"name": k, "count": n} for k, n in self.by[kind].most_common()]

    def regions(self):
        return [{"name": k, "count": n, "color": self.colors.get(k, FALLBACK_COLOR)} for k, n in self.by["region"].most_common()]

    def top(self, kind):
        out = []
        for key, n in sorted(self.by[kind].items(), key=lambda kv: (-kv[1], self.names[kind, kv[0]]))[:TOP]:
            region = self.home[kind, key].most_common(1)[0][0]
            out.append({"id": key, "name": self.names[kind, key], "region": region, "count": n,
                        "color": self.colors.get(region, FALLBACK_COLOR)})
        return out

    def grapes(self):
        """The most common grapes, each with its usual wine color; the rest summed as one entry (name None)."""
        ranked = sorted(self.by["grape"].items(), key=lambda kv: (-kv[1], kv[0]))
        out = [{"name": g, "count": n, "type": (self.grape_types[g].most_common(1) or [(None,)])[0][0]}
               for g, n in ranked[:TOP_GRAPES]]
        rest = ranked[TOP_GRAPES:]
        if rest:
            out.append({"name": None, "count": sum(n for _, n in rest), "type": None, "grapes": len(rest)})
        return out

    def vintages(self):
        """Each vintage, split by region (biggest first) for a column stacked in the regions' colors."""
        return [{"name": v, "count": n,
                 "regions": [{"name": r, "count": k, "color": self.colors.get(r, FALLBACK_COLOR)}
                             for r, k in self.vintage_regions[v].most_common()]}
                for v, n in sorted(self.by["vintage"].items(), key=lambda kv: vintage_key(kv[0]))]

    def charts(self):
        return {"total": self.total, "colors": self.counts("color"), "regions": self.regions(),
                "producers": self.top("producer"), "appellations": self.top("appellation"), "grapes": self.grapes(),
                "vintages": self.vintages()}


def region_colors(session):
    return {name: color for name, color in session.query(Region.name, Region.color) if color}


def michelin(session):
    """Stars of the restaurants visited (with or without wine): once per place, and once per visit day."""
    visited = union(select(TastingNote.place_id), select(RestaurantVisit.place_id)).subquery()
    by_stars = dict(session.query(Place.michelin_stars, func.count())
                    .filter(Place.michelin_stars > 0, Place.id.in_(select(visited.c.place_id)))
                    .group_by(Place.michelin_stars).all())
    days = union(select(TastingNote.date, TastingNote.place_id),
                 select(RestaurantVisit.date, RestaurantVisit.place_id)).subquery()
    total = session.execute(select(func.coalesce(func.sum(Place.michelin_stars), 0))
                            .join(days, days.c.place_id == Place.id).where(Place.michelin_stars > 0)).scalar()
    return {
        "unique_stars": sum(stars * n for stars, n in by_stars.items()),
        "total_stars": total,
        "restaurants": [{"stars": s, "count": by_stars.get(s, 0)} for s in (1, 2, 3)],
    }


def _wine(row, **extra):
    """A wine as the highlight cards list it: its name, region and color (the bottle end), and what it's there for."""
    return {"wine_id": row["wine_id"], "producer": row["producer"], "cuvee": row["cuvee"] or "",
            "vintage": row["vintage"], "region": row["region"], "color": row["color"], "format": row["format"], **extra}


def tasting_highlights(session, rows):
    """Your best-scored wines (each once, at its best), the places you've been most (days there, with or without
    wine) and the busiest evening (the most wines at one occasion)."""
    best = {}
    for r in rows:
        if r["rating"] is not None and (r["wine_id"] not in best or r["rating"] > best[r["wine_id"]]["rating"]):
            best[r["wine_id"]] = r
    top = sorted(best.values(), key=lambda r: (-r["rating"], -(r["date"].toordinal() if r["date"] else 0)))[:HIGHLIGHTS]

    days = union(select(TastingNote.date, TastingNote.place_id).where(TastingNote.place_id.isnot(None)),
                 select(RestaurantVisit.date, RestaurantVisit.place_id)).subquery()
    places = (session.query(Place.id, Place.name, Place.type, Place.city, func.count().label("visits"))
              .join(days, days.c.place_id == Place.id).group_by(Place.id)
              .order_by(func.count().desc(), Place.name).limit(HIGHLIGHTS).all())

    evenings = defaultdict(list)
    for r in rows:
        if r["date"]:
            evenings[r["date"], r["place_id"] or r["location"]].append(r)
    busiest = max(evenings.values(), key=lambda ws: (len(ws), ws[0]["date"]), default=[])
    busiest = sorted(busiest, key=lambda r: r["sequence"] or 0)
    return {
        "best": [_wine(r, id=r["tasting_id"], rating=r["rating"], date=r["date"].isoformat() if r["date"] else None)
                 for r in top],
        "places": [{"id": p.id, "name": p.name, "type": p.type, "city": p.city, "visits": p.visits} for p in places],
        "evening": {"date": busiest[0]["date"].isoformat(), "place_id": busiest[0]["place_id"],
                    "place": busiest[0]["place"] or busiest[0]["location"],
                    "wines": [_wine(r, id=r["tasting_id"]) for r in busiest]} if busiest else None,
    }


@router.get("/api/summary/tastings")
def tasting_summary(session: Session = Depends(get_session)):
    tally = Tally(region_colors(session))
    # Raw SQL: SQLite hands the dates back as text, Postgres as dates
    rows = [{**r, "date": date.fromisoformat(r["date"]) if isinstance(r["date"], str) else r["date"]}
            for r in session.execute(TASTINGS_SQL).mappings()]
    wines, ratings = set(), []
    for row in rows:
        tally.add(row)
        wines.add(row["wine_id"])
        if row["rating"] is not None:
            ratings.append(row["rating"])
    return {
        "wines": len(wines),
        "rated": len(ratings),
        "avg_rating": round(sum(ratings) / len(ratings), 1) if ratings else None,
        "michelin": michelin(session),
        "highlights": tasting_highlights(session, rows),
        **tally.charts(),
    }


def cellar_highlights(bottles):
    """The wines you hold the most of, the oldest vintages, and the bottles by storage place."""
    held = {}
    for b in bottles:
        w = held.setdefault(b["wine_id"], _wine(b, qty=0))
        w["qty"] += b["qty"]
    wines = list(held.values())
    largest = sorted(wines, key=lambda w: (-w["qty"], w["producer"]))[:HIGHLIGHTS]
    dated = [w for w in wines if str(w["vintage"])[:4].isdigit()]
    oldest = sorted(dated, key=lambda w: (str(w["vintage"])[:4], w["producer"]))[:HIGHLIGHTS]
    storage = Counter()
    for b in bottles:
        storage[b["location_group"]] += b["qty"]
    return {"largest": largest, "oldest": oldest,
            "storage": [{"name": k, "count": n} for k, n in storage.most_common()]}


@router.get("/api/summary/cellar")
def cellar_summary(session: Session = Depends(get_session)):
    bottles, _ = load_cellar(session)
    tally = Tally(region_colors(session))
    for b in bottles:
        tally.add(b, b["qty"])
    return {
        "wines": len({b["wine_id"] for b in bottles}),
        "value": round(sum(b["qty"] * b["price_base"] for b in bottles)),
        "market": round(sum(b["qty"] * b["market_base"] for b in bottles)),
        "highlights": cellar_highlights(bottles),
        **tally.charts(),
    }
