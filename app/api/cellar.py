"""Cellar inventory: one row per stocked bottle line, valued in the main currency (Settings), plus the physical shelf
layout."""
import re
from collections import defaultdict
from datetime import date

from sqlalchemy import event, text
from sqlalchemy.orm import Session

import scores
from display import vintage_label
import settings

# Both are edited on the Settings page (see settings.py), which updates them in place
EXCHANGE_RATES = dict(settings.current.exchange_rates)
# Locations containing these are outside the "local" totals (Settings)
NON_LOCAL_KEYWORDS = list(settings.current.non_local_keywords)

CELLAR_SQL = text("""
    SELECT b.id AS bottle_id, b.location, b.qty, b.bottle_size, b.price, b.currency,
           b.last_price, b.purchase_date, b.vendor,
           w.id AS wine_id, w.vineyard_id, w.type AS color, w.cuvee, w.vintage, w.disgorgement_date, pc.score AS score,
           w.lwin,
           w.drink_window_start, w.drink_window_end,
           p.id AS producer_id, p.name AS producer,
           r.name AS region, a.id AS appellation_id, a.name AS appellation, v.name AS varietal
    FROM cellar b
    JOIN wines w ON b.wine_id = w.id
    JOIN producers p ON w.producer_id = p.id
    LEFT JOIN regions r ON w.region_id = r.id
    LEFT JOIN appellations a ON w.appellation_id = a.id
    LEFT JOIN varietals v ON w.varietal_id = v.id
    LEFT JOIN critic_scores pc ON pc.wine_id = w.id AND LOWER(pc.critic) = LOWER(:critic)
    WHERE b.qty > 0
    ORDER BY r.name, p.name, w.vintage DESC
""")


def _storage_group(loc):
    matches = [g for g in settings.current.storage_groups if loc.startswith(g.prefix)]
    return max(matches, key=lambda g: len(g.prefix)) if matches else None


def location_group(loc):
    g = _storage_group(loc)
    return g.name if g else settings.current.other_group


def location_capacity(loc):
    # A location named like its group (e.g. "Home") is the overflow spot, not a sized bin
    g = _storage_group(loc)
    return g.capacity if g and loc != g.name else None


def location_sort_key(loc):
    # Natural sort so H2 < H10, then named bins (RA, RB...) after numbered ones
    m = re.match(r"([A-Za-z]+?)(\d+)$", loc)
    return (m.group(1), 0, int(m.group(2)), "") if m else (loc[:2], 1, 0, loc)


def to_base(amount, currency):
    """An amount in the main currency (a missing currency: the main one)."""
    return (amount or 0) * EXCHANGE_RATES.get(currency or settings.current.currency, 1.0)


def maturity(start, end, year=None):
    """Where a wine stands in its drinking window: "young", "ready", "past", or None without one."""
    if not start and not end:
        return None
    year = year or date.today().year
    if start and year < start:
        return "young"
    if end and year > end:
        return "past"
    return "ready"


GRAPES_SQL = """
    SELECT wg.wine_id, v.name FROM wine_grapes wg JOIN varietals v ON v.id = wg.varietal_id {where}
    ORDER BY wg.wine_id, wg.position
"""
IN_STOCK = "WHERE wg.wine_id IN (SELECT wine_id FROM cellar WHERE qty > 0)"


def grapes_by_wine(session, in_stock=False):
    """{wine_id: [its grapes' names, main grape first]}: what the cellar and tastings filter by grape on (in_stock:
    only the wines with bottles)."""
    out = defaultdict(list)
    for wine_id, name in session.execute(text(GRAPES_SQL.format(where=IN_STOCK if in_stock else ""))):
        out[wine_id].append(name)
    return out


@event.listens_for(Session, "after_flush")
def _forget_cellar(session, _context):
    session.info.pop("cellar", None)  # written to: read it again


def load_cellar(session):
    """(bottle lines, locations) of the cellar, read once per request: a page and its maps' figures share it."""
    if "cellar" not in session.info:
        session.info["cellar"] = _load_cellar(session)
    return session.info["cellar"]


def _load_cellar(session):
    bottles = []
    rows = session.execute(CELLAR_SQL, {"critic": scores.preferred()}).mappings().all()
    labels = scores.labels(session, [r["wine_id"] for r in rows])
    grapes = grapes_by_wine(session, in_stock=True)
    for r in rows:
        loc = r["location"] or "Unknown"
        vintage = vintage_label(r["vintage"], r["disgorgement_date"])
        price_base = to_base(r["price"], r["currency"])
        # Market price falls back to purchase price until a quote exists
        market_base = to_base(r["last_price"] if r["last_price"] else r["price"], r["currency"])
        bottles.append({
            "bottle_id": r["bottle_id"], "wine_id": r["wine_id"], "producer_id": r["producer_id"],
            "appellation_id": r["appellation_id"], "vineyard_id": r["vineyard_id"],
            "location": loc, "location_group": location_group(loc),
            "local": not any(k in loc for k in NON_LOCAL_KEYWORDS),  # counted in the local totals (Settings)
            "qty": r["qty"], "format": r["bottle_size"], "color": r["color"], "region": r["region"] or "Unknown",
            "producer": r["producer"], "cuvee": r["cuvee"] or "", "appellation": r["appellation"],
            "varietal": r["varietal"], "vintage": vintage,
            "grapes": grapes.get(r["wine_id"]) or ([r["varietal"]] if r["varietal"] else []),
            "price": r["price"], "currency": r["currency"], "last_price": r["last_price"],
            "price_base": round(price_base, 2), "market_base": round(market_base, 2),
            # the preferred critic's score (sorting), every critic's (shown)
            "score": r["score"] if scores.real(r["score"]) else None, "scores": labels.get(r["wine_id"]),
            "lwin": r["lwin"],
            "drink_from": r["drink_window_start"], "drink_to": r["drink_window_end"],
            "maturity": maturity(r["drink_window_start"], r["drink_window_end"]),
            "purchase_date": r["purchase_date"].isoformat() if hasattr(r["purchase_date"], "isoformat") else r["purchase_date"],
            "vendor": r["vendor"],
        })

    locations = [
        {"name": loc, "group": location_group(loc), "capacity": location_capacity(loc)}
        for loc in sorted({b["location"] for b in bottles}, key=location_sort_key)
    ]
    return bottles, locations
