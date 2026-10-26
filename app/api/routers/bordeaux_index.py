"""Your Bordeaux Index portfolio next to the app's own bottles and WineLabs values, in GBP."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import settings
from cellar import EXCHANGE_RATES, load_cellar
from db import Wine, get_session

router = APIRouter()



def held_at_bi(location):
    """Whether an app bottle is stored with Bordeaux Index (Settings › Bordeaux Index location: the warehouse holding them)."""
    keyword = (settings.current.bi_location or "").strip().lower()
    return bool(keyword) and keyword in (location or "").lower()


@router.get("/api/bordeaux-index")
def bordeaux_index(refresh: bool = False, session: Session = Depends(get_session)):
    """{"available", "error", "fetched", "lines": [...], "totals": {...}, "app_only": [...]}: each BI line per bottle
    in GBP (cost, best bid, best offer, last trade) with the app's bottles of that wine, vintage and size held at BI
    (location containing Settings' bi_location: the warehouse holding them), and the app's bottles there that BI doesn't list."""
    from winelib_utils import bordeaux_index as bi
    if not bi.configured():
        return {"available": False, "error": "No Bordeaux Index login in .secrets.env (BI_EMAIL, BI_PASSWORD, "
                                             "BI_SALES_LEDGER, BI_PURCHASE_LEDGER)", "lines": [], "totals": None}
    try:
        items, fetched = bi.cached_portfolio(refresh)  # shared with pricing, kept a few minutes
    except bi.BIError as e:
        return {"available": True, "error": str(e), "lines": [], "totals": None}

    gbp = EXCHANGE_RATES.get("GBP", 1.0)
    bottles, _ = load_cellar(session)
    at_bi = [b for b in bottles if held_at_bi(b["location"])]
    by_wine = {}
    for b in at_bi:
        if b["lwin"]:
            key = (str(b["lwin"]), bi.vintage_key(b["vintage"]), bi.size_cl(b["format"]))
            by_wine.setdefault(key, []).append(b)

    def app_side(mine, how):
        return {
            "bottles": sum(b["qty"] for b in mine),
            "locations": sorted({b["location"] for b in mine}),
            "value": round(sum(b["qty"] * b["market_base"] for b in mine) / gbp, 2),
            "bottle_ids": [b["bottle_id"] for b in mine],
            # the (first) matched wine's region and color, for its bottle end
            "region": mine[0]["region"] if mine else None,
            "color": mine[0]["color"] if mine else None,
            "match": how if mine else None,
            # wines whose LWIN differs from BI's (matched by name): the view offers to take BI's
            "fix": sorted({(b["wine_id"], b["lwin"] or "") for b in mine}) if how == "name" else [],
        }

    parsed = [bi.line(it) for it in items]
    matched = set()
    for line in parsed:  # by LWIN, vintage and size
        mine = by_wine.get((line["lwin7"], line["vintage"], line["size_cl"]), [])
        matched.update(b["bottle_id"] for b in mine)
        line["app"] = app_side(mine, "lwin")
    for line in parsed:  # mixed cases (ASSORTMENTS): the app holds each wine of the case on its own
        rule = bi.assortment(line)
        if rule and not line["app"]["bottles"]:
            cases = line["cases"] or 0
            mine, parts = [], []
            for word, per_case in rule["parts"]:
                held = [b for b in at_bi if b["bottle_id"] not in matched and bi.assortment_part(rule, line, b) == word]
                mine += held
                parts.append({"name": word.title(), "expected": per_case * cases, "held": sum(b["qty"] for b in held)})
            matched.update(b["bottle_id"] for b in mine)
            line["app"] = {**app_side(mine, "assortment"), "parts": parts}
    for line in parsed:  # then by name, for what's left: the app's LWIN may be another wine's (Les / Clos des Angles)
        if not line["app"]["bottles"]:
            mine = [b for b in at_bi if b["bottle_id"] not in matched and bi.same_wine_by_name(line, b)]
            matched.update(b["bottle_id"] for b in mine)
            line["app"] = app_side(mine, "name")

    lines = []
    for line in parsed:
        # BI's valuation: the last trade, else the best bid, else (neither) what you paid. Only a last trade
        # prices the app's bottles (bi.quotes, apply_values)
        unit = line["unit"] or line["cost"]
        line["basis"] = "last" if line["last"] else "bid" if line["bid"] else "cost" if line["cost"] else None
        line["value"] = round(unit * line["bottles"], 2) if unit else None
        line["lwin"] = line.pop("lwin7")
        for k in ("size_cl", "unit"):
            line.pop(k)
        lines.append(line)
    lines.sort(key=lambda l: -(l["value"] or 0))

    # Held at BI according to the app, but not in the BI portfolio (or not matched: no LWIN, another vintage or size)
    app_only = [{"bottle_id": b["bottle_id"], "producer": b["producer"], "cuvee": b["cuvee"], "vintage": b["vintage"],
                 "format": b["format"], "region": b["region"], "color": b["color"],
                 "qty": b["qty"], "location": b["location"], "lwin": b["lwin"],
                 "value": round(b["qty"] * b["market_base"] / gbp, 2)}
                for b in at_bi if b["bottle_id"] not in matched]
    app_only.sort(key=lambda b: (b["producer"], b["cuvee"], b["vintage"]))

    def total(key):
        return round(sum((l[key] or 0) * l["bottles"] for l in lines), 2)
    totals = {"bottles": sum(l["bottles"] for l in lines), "cost": total("cost"), "bid": total("bid"),
              "last": total("last"), "value": round(sum(l["value"] or 0 for l in lines), 2),
              # each matched app bottle once, even when BI splits a wine over several lines
              # BI's value of the lines found in the app, to set against app_value
              "value_matched": round(sum(l["value"] or 0 for l in lines if l["app"]["bottles"]), 2),
              "app_value": round(sum(b["qty"] * b["market_base"] for b in at_bi if b["bottle_id"] in matched) / gbp, 2),
              "app_bottles": sum(b["qty"] for b in at_bi),
              "unmatched": sum(1 for l in lines if not l["app"]["bottles"]),
              "by_name": sum(1 for l in lines if l["app"]["match"] == "name"),
              "app_only": sum(b["qty"] for b in app_only)}
    return {"available": True, "error": None, "fetched": fetched, "location": settings.current.bi_location,
            "lines": lines, "totals": totals, "app_only": app_only}


class UseLwin(BaseModel):
    wine_id: int
    lwin: str = Field(pattern=r"^\d{7}$")


@router.post("/api/bordeaux-index/use-lwin")
def use_lwin(body: UseLwin, session: Session = Depends(get_session)):
    """Gives an app wine the LWIN Bordeaux Index uses for it (a name match whose LWINs differed)."""
    wine = session.get(Wine, body.wine_id)
    if wine is None:
        raise HTTPException(404, "Wine not found")
    old, wine.lwin = wine.lwin, body.lwin
    session.commit()
    return {"wine_id": wine.id, "old": old, "lwin": wine.lwin}


class ApplyValues(BaseModel):
    commit: bool = False


@router.post("/api/bordeaux-index/apply-values")
def apply_values(body: ApplyValues, session: Session = Depends(get_session)):
    """BI's last trade per bottle as the market price of the app's bottles each BI line matched, in each bottle's
    currency (lines without a trade are left out): {"changes": [...], "saved"}. A preview unless commit."""
    from datetime import datetime

    from db import Bottle
    from winelib_utils import update_market_prices as prices
    view = bordeaux_index(refresh=False, session=session)
    if view.get("error") or not view.get("available"):
        raise HTTPException(503, view.get("error") or "No Bordeaux Index login")
    rates = prices.exchange_rates(session)
    changes, missing = {}, set()
    for line in view["lines"]:
        if line["basis"] != "last" or not line["last"] or not line["app"]["bottle_ids"]:
            continue
        unit_gbp = line["last"]
        for bottle_id in line["app"]["bottle_ids"]:
            b = session.get(Bottle, bottle_id)
            currency = (b.currency or settings.current.currency).upper()
            if currency != "GBP" and ("GBP" not in rates or currency not in rates):
                missing.add(currency)
                continue
            new = unit_gbp if currency == "GBP" else unit_gbp * rates["GBP"] / rates[currency]
            changes[bottle_id] = {"bottle_id": bottle_id, "wine": " ".join(
                x for x in (b.wine.producer.name, b.wine.cuvee or "", b.wine.vintage or "") if x),
                "region": b.wine.region_obj.name if b.wine.region_obj else None, "color": b.wine.type, "format": b.bottle_size,
                "qty": b.qty, "currency": currency, "old": b.last_price, "new": round(new, 2), "basis": line["basis"],
                "assortment": line["app"]["match"] == "assortment"}
    if body.commit:
        now = datetime.now()
        for c in changes.values():
            b = session.get(Bottle, c["bottle_id"])
            b.last_price, b.last_price_date, b.last_price_source = c["new"], now, "Bordeaux Index"
        session.commit()
    return {"changes": sorted(changes.values(), key=lambda c: c["wine"]), "saved": len(changes) if body.commit else 0,
            "missing_rates": sorted(missing)}
