"""What needs your attention, for the home page: the Maintenance checks quick enough to run on every visit, each with
how many things it found and the task that sorts them out (Settings › Maintenance, opened on its preview).

`GET /api/attention`: {"items": [{"id", "level", "title", "detail", "count", "task"}]}, the warnings first; none when
all is well. A check that fails is left out (the page must load whatever happens).
"""
import logging
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from db import get_session

router = APIRouter()
log = logging.getLogger(__name__)

WARN, INFO = "warn", "info"


def _n(n, word, plural=None):
    return f"{n} {word if n == 1 else plural or word + 's'}"


def _duplicates(session):
    from tasks.consolidate_duplicate_wines import find_duplicate_groups
    groups = find_duplicate_groups(session)
    if groups:
        return WARN, f"{_n(len(groups), 'wine')} entered twice", ", ".join(g["label"] for g in groups[:3]), len(groups), "duplicates"


def _orphans(session):
    from tasks.housekeeping.check_orphans import find_orphans
    r = find_orphans(session)
    n = len(r["notes"]) + len(r["bottles"])
    if n:
        return WARN, f"{_n(n, 'record')} pointing at nothing", \
            f"{_n(len(r['notes']), 'tasting note')} without a bottle, {_n(len(r['bottles']), 'bottle')} without a wine", n, "orphans"


def _twice_under_two_appellations(session):
    from tasks import vintages
    found = [c for c in vintages.appellations_apart(session) if c["both"]]
    if found:
        names = ", ".join(f"{c['wine'].producer.name} {c['wine'].cuvee} {'/'.join(c['both'])}" for c in found[:3])
        return WARN, f"{_n(len(found), 'vintage')} under two appellations", names, len(found), "appellations_apart"


def _stale_prices(session):
    """Bottles in the cellar whose market price is older than twice the refresh age (the nightly refresh failing)."""
    from routers.maintenance import _no_price_source
    from tasks.update_market_prices import PRICE_MAX_AGE_DAYS
    if _no_price_source():
        return None
    since = date.today() - timedelta(days=2 * PRICE_MAX_AGE_DAYS)
    n = session.execute(text("""SELECT count(*) FROM cellar b JOIN wines w ON w.id = b.wine_id
        WHERE b.qty > 0 AND coalesce(w.lwin, '') <> '' AND (b.last_price_date IS NULL OR b.last_price_date < :since)"""),
        {"since": since}).scalar()
    if n:
        return WARN, f"{_n(n, 'bottle')} without a recent market price", \
            f"none in {2 * PRICE_MAX_AGE_DAYS} days: is the nightly refresh running?", n, "prices"


def _no_lwin(session):
    """Wines in the cellar without an LWIN, when prices come by it."""
    from routers.maintenance import _no_lwin_list, _no_price_source
    if _no_price_source() or _no_lwin_list():
        return None
    n = session.execute(text("""SELECT count(DISTINCT w.id) FROM cellar b JOIN wines w ON w.id = b.wine_id
        WHERE b.qty > 0 AND coalesce(w.lwin, '') = ''""")).scalar()
    if n:
        return INFO, f"{_n(n, 'wine')} in the cellar without an LWIN", "no market price for them until they have one", n, "lwin"


# Places that aren't somewhere on a map: a friend's home, a flight
NOT_ON_A_MAP = ("Friend's Place", "Flight", "Airline", "Home")


def _places(session):
    n = session.execute(text("SELECT count(*) FROM places WHERE (lat IS NULL OR lng IS NULL) "
                             "AND coalesce(type, '') NOT IN :skip").bindparams(bindparam("skip", expanding=True)),
                        {"skip": list(NOT_ON_A_MAP)}).scalar()
    if n:
        return INFO, f"{_n(n, 'place')} not on the map", "restaurants and bars without coordinates", n, "places"


def _outlines(session):
    import geo
    if not geo.outlines_installed():
        return INFO, "No map outlines installed", "the maps show regions only", 1, "map_pack"


CHECKS = [_duplicates, _orphans, _twice_under_two_appellations, _stale_prices, _no_lwin, _places,
          _outlines]


@router.get("/api/attention")
def attention(session: Session = Depends(get_session)):
    items = []
    for check in CHECKS:
        try:
            found = check(session)
        except Exception:
            log.exception("Attention check %s failed", check.__name__)
            session.rollback()
            continue
        if found:
            level, title, detail, count, task = found
            items.append({"id": check.__name__.strip("_"), "level": level, "title": title, "detail": detail,
                          "count": count, "task": task})
    items.sort(key=lambda i: i["level"] != WARN)
    return {"items": items}
