"""A demo database cut from yours: the producers you hold and drink the most, with their wines, bottles, tastings and
the places of those tastings, on the reference data a new installation gets. For screenshots, a public demo, trying a
change on real-looking data. Your database is only read.

Left out: what bottles cost and where they come from (price, currency, vendor, provenance, purchase date, market
prices), critics' review texts (copyrighted: scores and links stay), your notes on producers and places, vineyards
other than INAO's public premier crus, photos, drawn outlines, Bordeaux Index.

--public (screenshots, the public demo) also makes it anyone's: neutral settings (euros, a Home / Wine room /
Warehouse cellar), bins renamed (one that isn't a shelf: Away), and private places (homes, friends', an office: by
their type) given a generic name and no coordinates (a friend's: a made-up first name); restaurants, bars and
wineries stay. The notes' text goes (tastings and visits keep their date, score and place): it names people.

    python scripts/make_demo_db.py --from postgresql://user:pw@db-host:5432/winelib_db          # data/demo.db
    python scripts/make_demo_db.py --from sqlite:///data/winelib.db --producers 30 --to sqlite:///other.db
    python scripts/make_demo_db.py --from <your DB_URL> --public                              # for the public eye
    DB_URL=sqlite:///../../data/demo.db uvicorn main:app                                      # from app/api
"""
import argparse
import os
import sys

from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_TO = f"sqlite:///{os.path.join(ROOT, 'data', 'demo.db')}"
sys.path.insert(0, ROOT)

from winelib_utils.models import (  # noqa: E402
    Appellation, Bottle, CriticScore, Place, Producer, Region, RestaurantVisit, TastingNote, Varietal, Vineyard, Wine)

# Columns copied (the others are left out, see the docstring)
PRODUCER = ["name", "subregion", "village", "winemaker", "owner", "type", "description", "website", "aliases"]
WINE = ["cuvee", "vintage", "disgorgement_date", "type", "blend", "lwin", "drink_window_start", "drink_window_end"]
BOTTLE = ["location", "bottle_size", "qty"]
TASTING = ["date", "rating", "notes", "tags", "location", "sequence", "glasses"]
PLACE = ["name", "city", "country", "type", "michelin_stars", "lat", "lng"]


def top_producers(src, n):
    """The ids of the n producers with the most bottles and tastings."""
    bottles = dict(src.query(Wine.producer_id, func.coalesce(func.sum(Bottle.qty), 0))
                   .join(Bottle, Bottle.wine_id == Wine.id).group_by(Wine.producer_id).all())
    tasted = dict(src.query(Wine.producer_id, func.count(TastingNote.id)).join(Bottle, Bottle.wine_id == Wine.id)
                  .join(TastingNote, TastingNote.bottle_id == Bottle.id).group_by(Wine.producer_id).all())
    ranked = sorted(set(bottles) | set(tasted), key=lambda p: (-(bottles.get(p, 0) + tasted.get(p, 0)), p))
    return ranked[:n]


class Refs:
    """The demo's row for a reference row of yours: the same id when it's the same row (the reference data comes
    from your database), else by name; None when it has none (a vineyard that doesn't ship)."""

    def __init__(self, src, dst):
        self.src, self.dst, self.cache = src, dst, {}

    def __call__(self, model, ref_id):
        if ref_id is None:
            return None
        key = (model, ref_id)
        if key not in self.cache:
            mine = self.src.get(model, ref_id)
            same = self.dst.get(model, ref_id)
            if mine is None:
                self.cache[key] = None
            elif same is not None and same.name == mine.name:
                self.cache[key] = same.id
            else:
                row = self.dst.query(model.id).filter(model.name == mine.name).order_by(model.id).first()
                self.cache[key] = row[0] if row else None
        return self.cache[key]


def copy(src, dst, n=20):
    """Copies the n most represented producers and what goes with them into dst (empty but for the reference
    data). Counts of the rows copied."""
    if dst.query(Wine).count():
        raise SystemExit("The demo database has wines already: start from an empty one.")
    ref = Refs(src, dst)
    take = lambda row, cols: {c: getattr(row, c) for c in cols}  # noqa: E731
    counts = dict.fromkeys(["producers", "wines", "scores", "bottles", "tastings", "places", "visits"], 0)
    places = {}  # your place id -> the demo's Place

    def place(pid):
        if pid is not None and pid not in places:
            p = src.get(Place, pid)
            places[pid] = Place(**take(p, PLACE)) if p else None
            if places[pid] is not None:
                dst.add(places[pid])
                counts["places"] += 1
        return places.get(pid)

    for pid in top_producers(src, n):
        p = src.get(Producer, pid)
        # The reference data ships producers: the demo's row is the reference one when it's there
        producer = dst.query(Producer).filter(Producer.name == p.name).first()
        if producer is None:
            producer = Producer(**take(p, PRODUCER), region_id=ref(Region, p.region_id))
            dst.add(producer)
        counts["producers"] += 1
        for w in src.query(Wine).filter(Wine.producer_id == pid).order_by(Wine.id):
            wine = Wine(producer=producer, **take(w, WINE), region_id=ref(Region, w.region_id),
                        appellation_id=ref(Appellation, w.appellation_id), varietal_id=ref(Varietal, w.varietal_id),
                        vineyard_id=ref(Vineyard, w.vineyard_id))
            dst.add(wine)
            grapes = [(dst.get(Varietal, ref(Varietal, g.varietal_id)), g.share) for g in w.grapes]
            if grapes and all(v is not None for v, _ in grapes):  # its grapes, the main one first (a blend's too)
                wine.set_grapes(grapes)
            counts["wines"] += 1
            for s in w.scores:  # the score and its link, not the review's text
                wine.scores.append(CriticScore(critic=s.critic, score=s.score, url=s.url, date=s.date))
                counts["scores"] += 1
            for b in src.query(Bottle).filter(Bottle.wine_id == w.id).order_by(Bottle.id):
                bottle = Bottle(wine=wine, **take(b, BOTTLE))
                dst.add(bottle)
                counts["bottles"] += 1
                for t in src.query(TastingNote).filter(TastingNote.bottle_id == b.id).order_by(TastingNote.id):
                    dst.add(TastingNote(bottle=bottle, **take(t, TASTING), place=place(t.place_id)))
                    counts["tastings"] += 1
    for pid, demo_place in places.items():  # the visits to those places
        if demo_place is None:
            continue
        for v in src.query(RestaurantVisit).filter(RestaurantVisit.place_id == pid).order_by(RestaurantVisit.id):
            dst.add(RestaurantVisit(place=demo_place, date=v.date, notes=v.notes))
            counts["visits"] += 1
    dst.commit()
    return counts


# --public: places that are someone's (by their type), named by it and left without coordinates
PRIVATE_PLACES = {"Home": "Home", "People": "Friend", "Friend's Place": "Friend", "Office": "Office",
                  "Other": "Elsewhere", "Unknown": "Elsewhere", "Event": "A tasting", "Flight": "On a flight",
                  "Club": "A club"}
# Friends' places (the type Friend's Place, shown as a house and who): a first name each (made up, and unique:
# place names are)
FRIENDS = ["Alex", "Sam", "Charlie", "Robin", "Jo", "Max", "Camille", "Dominique", "Leslie", "Morgan", "Noa", "Kim",
           "Lou", "Eden", "Sacha", "Andrea", "Jules", "Ariel", "Taylor", "Jordan", "Remy", "Claude", "Avery", "Quinn",
           "Rowan", "Sasha", "Elliot", "Hayden", "Marion", "Nicky"]


def make_public(dst, settings):
    """Neutral settings, bins and private places (see --public in the docstring)."""
    import re
    from collections import Counter
    shelves = {}  # your bin -> the demo's
    letters = 12
    bi = settings.load(dst).bi_location  # bottles held at Bordeaux Index's warehouse
    for (loc,) in dst.query(Bottle.location).distinct().order_by(Bottle.location):
        if not loc or loc in ("Consumed", "Home") or re.fullmatch(r"H\d+", loc):
            continue
        if m := re.fullmatch(r"WB(\d+)", loc):
            shelves[loc] = f"R{m.group(1)}"
        elif loc.startswith("WB"):
            letters += 1
            shelves[loc] = f"R{letters}"
        elif bi and loc.startswith(bi):
            shelves[loc] = "Warehouse"
        else:
            shelves[loc] = "Away"
    for b in dst.query(Bottle).filter(Bottle.location.in_(list(shelves))):
        b.location = shelves[b.location]
    # Notes name people ("with Antoine and Yann"): their text goes, the tastings stay
    dst.query(TastingNote).update({TastingNote.notes: None})
    dst.query(RestaurantVisit).update({RestaurantVisit.notes: None})
    seen = Counter()
    for p in dst.query(Place).order_by(Place.id):
        if p.type in PRIVATE_PLACES:
            name = PRIVATE_PLACES[p.type]
            seen[name] += 1
            n = seen[name]
            if name == "Friend":
                p.type = "Friend's Place"
                p.name = FRIENDS[n - 1] if n <= len(FRIENDS) else f"{FRIENDS[(n - 1) % len(FRIENDS)]} {n}"
            else:
                p.name = name if n == 1 else f"{name} ({n})"
            p.lat = p.lng = None
    settings.save(dst, settings.Settings(
        currency="EUR", local_label="Home", non_local_keywords=["Warehouse", "Away"], other_group="Away",
        storage_groups=[{"name": "Home", "prefix": "H", "capacity": 10}, {"name": "Wine room", "prefix": "R", "capacity": 12},
                        {"name": "Warehouse", "prefix": "Warehouse", "capacity": 1000}],
        map_default_basemap="plain", preferred_critic="Robert Parker"))
    dst.commit()


def your_settings(src, settings):
    """Your settings (storage groups, currencies, preferred critic), read without writing anything."""
    import json
    from sqlalchemy import inspect
    if not inspect(src.get_bind()).has_table(settings.AppSettingsRow.__tablename__):
        return settings.Settings()
    row = src.get(settings.AppSettingsRow, 1)
    return settings.Settings(**json.loads(row.data)) if row else settings.Settings()


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--from", dest="source", default=os.getenv("DB_URL"), help="your database (read only)")
    parser.add_argument("--to", default=DEFAULT_TO, help="the demo database (new or empty)")
    parser.add_argument("--producers", type=int, default=20, help="how many producers (the most represented)")
    parser.add_argument("--public", action="store_true", help="neutral settings, bins and private places (see above)")
    args = parser.parse_args()
    if not args.source:
        sys.exit("Which database to cut from? --from (or DB_URL)")
    os.environ["DB_URL"] = args.to  # the app's modules read it on import
    sys.path.insert(0, os.path.join(ROOT, "app", "api"))
    import migrate
    import reference
    import settings
    target = create_engine(args.to)
    migrate.upgrade(target)
    reference.seed(target)
    with Session(create_engine(args.source)) as src, Session(target) as dst:
        counts = copy(src, dst, args.producers)
        settings.save(dst, your_settings(src, settings).model_copy(update={"bi_location": ""}))
        if args.public:
            make_public(dst, settings)
    print(f"Demo database {target.url.render_as_string(hide_password=True)}: "
          + ", ".join(f"{n} {k}" for k, n in counts.items()))


if __name__ == "__main__":
    main()
