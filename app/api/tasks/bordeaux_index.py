"""Bordeaux Index LiveTrade API (https://api.biwine.com/swagger-ui): your BI portfolio with its live bids, offers and
last trades. Read only: this module never places or changes an order.

Credentials in .secrets.env: BI_EMAIL, BI_PASSWORD, BI_SALES_LEDGER, BI_PURCHASE_LEDGER (an approved API access).
Prices are in GBP, per case of the line's pack size.
"""
import json
import os
import re
import unicodedata
import time
import urllib.error
import urllib.request

from tasks import USER_AGENT

BI_API = os.getenv("BI_API", "https://api.biwine.com")

_token = {"value": None, "until": 0.0}


class BIError(Exception):
    pass


def configured():
    return all(os.getenv(k) for k in ("BI_EMAIL", "BI_PASSWORD", "BI_SALES_LEDGER", "BI_PURCHASE_LEDGER"))


def _request(method, path, body=None, token=None, timeout=30):
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BI_API + path, data=json.dumps(body).encode() if body is not None else None,
                                 method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            message = json.load(e).get("message") or e.reason
        except Exception:
            message = e.reason
        raise BIError(f"{e.code} {message}") from e
    except (urllib.error.URLError, TimeoutError) as e:
        raise BIError(f"Bordeaux Index couldn't be reached: {getattr(e, 'reason', e)}") from e


def token():
    """A bearer token, logging in again shortly before the last one expires (they last 24 hours)."""
    if _token["value"] and time.time() < _token["until"]:
        return _token["value"]
    if not configured():
        raise BIError("No Bordeaux Index login: set BI_EMAIL, BI_PASSWORD, BI_SALES_LEDGER and BI_PURCHASE_LEDGER "
                      "in .secrets.env")
    try:
        r = _request("POST", "/v2/user/login", {
            "email": os.getenv("BI_EMAIL"), "password": os.getenv("BI_PASSWORD"),
            "salesLedger": os.getenv("BI_SALES_LEDGER"), "purchaseLedger": os.getenv("BI_PURCHASE_LEDGER")})
    except BIError as e:
        raise BIError(f"Bordeaux Index refused the login ({e}): check the BI_ lines in .secrets.env") from e
    expiry = r.get("expiry") or 3600
    expiry = expiry / 1000 if expiry > 10 ** 8 else expiry  # seconds (or milliseconds)
    _token.update(value=r["token"], until=time.time() + min(expiry, 23 * 3600) - 300)
    return _token["value"]


def portfolio():
    """Every line of your BI portfolio (all pages), with its best bid and offer."""
    lines, page = [], 0
    while True:
        r = _request("GET", f"/v2/portfolio?page={page}&limit=500&marketDepth=1", token=token())
        lines += r.get("results") or []
        meta = r.get("meta") or {}
        if page >= (meta.get("finalPage") or 0):
            return lines
        page += 1


# The portfolio, shared by the Cellar view and pricing for a few minutes: clicking "market price" on several
# bottles, or opening the view after a price run, doesn't read it again. In memory only: bids and offers saved
# to disk would go stale unnoticed.
PORTFOLIO_MAX_AGE = 600
_portfolio = {"at": 0.0, "lines": None}


def cached_portfolio(refresh=False):
    """(portfolio lines, time read): the copy from the last PORTFOLIO_MAX_AGE seconds, else read again (refresh:
    always read again)."""
    if refresh or _portfolio["lines"] is None or time.time() - _portfolio["at"] > PORTFOLIO_MAX_AGE:
        _portfolio.update(lines=portfolio(), at=time.time())
    return _portfolio["lines"], _portfolio["at"]


def forget_portfolio():
    _portfolio.update(at=0.0, lines=None)


def split_lwin18(lwin18):
    """LWIN18 → (LWIN7, vintage, pack size, bottle size in ml): 100006920071200750 → ("1000069", "2007", 12, 750)."""
    s = str(lwin18 or "")
    if len(s) != 18 or not s.isdigit():
        return None, None, None, None
    return s[:7], s[7:11], int(s[11:13]), int(s[13:])


def per_bottle(case_price, pack):
    return round(case_price / pack, 2) if case_price and pack else None


# Bottle sizes in cl, so "75cl", "750ml", "0.75l" and BI's 75 compare equal
NAMED_SIZES = {"half": 37.5, "demi": 37.5, "magnum": 150, "double magnum": 300, "jeroboam": 300, "rehoboam": 450,
               "imperiale": 600, "impériale": 600, "methuselah": 600, "salmanazar": 900}


def size_cl(size):
    """A bottle size in cl: 75 for "75cl", "750ml", "0.75l", 75 or nothing (the usual bottle); None if unknown."""
    if size is None or size == "":
        return 75.0
    if isinstance(size, (int, float)):
        return float(size)
    text = str(size).strip().lower().replace(",", ".")
    if text in NAMED_SIZES:
        return float(NAMED_SIZES[text])
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(cl|ml|l)?", text)
    if not m:
        return None
    n, unit = float(m.group(1)), m.group(2) or "cl"
    return n / 10 if unit == "ml" else n * 100 if unit == "l" else n


def vintage_key(vintage):
    """A vintage both sides agree on: "2019", or "NV" for BI's 1000 and the app's "NV" / "NV - Oct 2024" / blank."""
    text = str(vintage or "").strip().upper()
    if not text or text.startswith("NV") or text == "1000":
        return "NV"
    m = re.search(r"\b(1[89]\d\d|20\d\d)\b", text)
    return m.group(1) if m else text


# Words that don't tell two wines of a producer apart: "Clos des Angles" and "Les Angles" are the same name here
NAME_NOISE = {
    "clos", "les", "le", "la", "l", "des", "de", "du", "d", "et", "en", "sur", "aux", "au", "the", "domaine", "dom",
    "chateau", "ch", "maison", "cru", "premier", "1er", "grand", "gc", "pc", "vieilles", "vignes", "vv", "cuvee",
    "rouge", "blanc", "red", "white", "brut", "aoc", "aop", "village", "villages",
}


def name_tokens(text):
    """The distinctive words of a wine name, accents and case folded, without NAME_NOISE."""
    text = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode().lower()
    return {w for w in re.split(r"[^a-z0-9]+", text) if w and w not in NAME_NOISE and not w.isdigit()}


def same_wine_by_name(line, bottle):
    """Whether a BI line and an app bottle look like the same wine although their LWINs differ: same vintage and
    size, the producer's words in common, and the wine's own words (BI's name without the producer, the app's
    cuvée and appellation) overlapping."""
    if line["vintage"] != vintage_key(bottle["vintage"]) or line["size_cl"] != size_cl(bottle["format"]):
        return False
    producer = name_tokens(bottle["producer"])
    bi_producer = name_tokens(line["producer"]) or producer
    if not producer or not (producer & name_tokens(line["name"]) or producer & bi_producer):
        return False
    bi_words = name_tokens(line["name"]) - producer - bi_producer
    appellation = name_tokens(bottle["appellation"])
    cuvee = name_tokens(bottle["cuvee"]) - producer
    specific = bi_words - appellation  # what BI's name says beyond the appellation: the cuvée or climat
    if not cuvee:
        # No cuvée in the app: BI's name must be just the producer and that appellation
        return bool(bi_words & appellation) and not specific
    shared = cuvee & specific
    # Most of each side's own words in common (not merely the appellation: Champans isn't Clos des Angles)
    return bool(shared) and len(shared) / len(specific) >= 0.5 and len(shared) / len(cuvee) >= 0.5


# The mixed cases BI sells as one line, which the app holds as separate wines (add one here when you hold another).
# Each: the producer's word, the words BI's name must carry, and per case the app's cuvées (a distinctive word of
# each) and how many bottles of each.
ASSORTMENTS = [
    {"producer": "guigal", "name": {"rotie", "assortment"},
     "parts": [("landonne", 1), ("mouline", 1), ("turque", 1)]},  # La Landonne, La Mouline, La Turque
]


def assortment(line):
    """The ASSORTMENTS rule a BI line falls under, or None."""
    words = name_tokens(line["name"]) | name_tokens(line["producer"])
    return next((a for a in ASSORTMENTS if a["producer"] in words and a["name"] <= words), None)


def assortment_part(rule, line, bottle):
    """Which of an assortment's parts (its cuvée word) an app bottle is, or None: same producer, vintage and size."""
    if line["vintage"] != vintage_key(bottle["vintage"]) or line["size_cl"] != size_cl(bottle["format"]):
        return None
    if rule["producer"] not in name_tokens(bottle["producer"]):
        return None
    cuvee = name_tokens(bottle["cuvee"])
    return next((word for word, _ in rule["parts"] if word in cuvee), None)


def size_label(cl):
    return f"{cl:g}cl" if cl else "?"


def line(it):
    """One portfolio entry, normalised: the wine (LWIN7, vintage, size in cl), bottles held and its prices per
    bottle in GBP. "unit" is BI's valuation of a bottle: the last trade, else the best bid."""
    lwin7, vintage, pack, ml = split_lwin18(it.get("lwin18"))
    pack = it.get("packSize") or pack or 1
    cl = size_cl(it.get("size") or (ml / 10 if ml else None))
    bids = [o.get("price") for o in (it.get("bids") or it.get("rolledUpBids") or []) if o.get("price")]
    offers = [o.get("price") for o in (it.get("offers") or it.get("rolledUpOffers") or []) if o.get("price")]
    last = it.get("lastTrade") or {}
    out = {
        "ref": it.get("portfolioRef"), "name": it.get("lwinProductName") or it.get("productName"),
        "producer": it.get("producer"), "lwin7": lwin7, "vintage": vintage_key(it.get("vintageYear") or vintage),
        "pack": pack, "size_cl": cl, "size": size_label(cl), "cases": it.get("quantity"),
        "bottles": (it.get("quantity") or 0) * pack,  # quantity is in cases
        "location": it.get("location"), "duty": it.get("dutyStatus"), "url": it.get("url"), "lwin18": it.get("lwin18"),
        "cost": per_bottle(it.get("costPrice"), pack),
        "bid": per_bottle(max(bids), pack) if bids else None,
        "offer": per_bottle(min(offers), pack) if offers else None,
        "last": per_bottle(last.get("price"), pack), "last_date": last.get("date"),
    }
    out["unit"] = out["last"] or out["bid"]
    return out


# Pack sizes to try, most common first, when asking the market for a wine the app holds (it doesn't know the pack)
MARKET_PACKS = {75.0: (6, 12, 3, 1), 150.0: (3, 6, 1), 37.5: (12, 24, 6), 300.0: (1, 3), 600.0: (1,)}


def lwin18(lwin7, vintage, pack, cl):
    """LWIN18 = LWIN7 + vintage (1000 for NV) + pack (2 digits) + bottle size in ml (5 digits), or None."""
    v = vintage_key(vintage)
    v = "1000" if v == "NV" else v
    if not (str(lwin7 or "").isdigit() and len(str(lwin7)) == 7 and v.isdigit() and len(v) == 4 and cl):
        return None
    return f"{lwin7}{v}{int(pack):02d}{int(round(cl * 10)):05d}"


def market(code):
    """The LiveTrade market for one LWIN18 (GET /v2/market/lwin18/{lwin18}): its entries, [] when there's none."""
    try:
        r = _request("GET", f"/v2/market/lwin18/{code}", token=token())
    except BIError as e:
        if str(e).startswith(("404", "400")):
            return []
        raise
    items = r.get("results", r) if isinstance(r, dict) else r
    return [items] if isinstance(items, dict) else list(items or [])


def market_quote(lwin7, vintage, cl):
    """GBP per bottle for a wine on the LiveTrade market: its last trade, trying the usual pack sizes; None when it
    hasn't traded (a bid isn't a price: WineLabs then)."""
    for pack in MARKET_PACKS.get(cl, (6, 12, 1)):
        code = lwin18(lwin7, vintage, pack, cl)
        if not code:
            return None
        for it in market(code):
            it = {"lwin18": code, "packSize": pack, "size": cl, **it}
            last = line(it)["last"]
            if last:
                return last
    return None


def quotes(lines):
    """{(LWIN7, vintage, size in cl): GBP per bottle} from normalised lines, for pricing the app's bottles: the last
    trade only (a bid isn't a price: WineLabs then)."""
    out = {}
    for l in lines:
        if l["lwin7"] and l["last"] and not assortment(l):  # a mixed case's price isn't one wine's
            out.setdefault((l["lwin7"], l["vintage"], l["size_cl"]), l["last"])
    return out
