"""Market prices for cellar bottles, by the wine's LWIN: Bordeaux Index first, WineLabs.ai for the rest.

Bordeaux Index's valuation (the last trade, else the best bid, per bottle in GBP, converted to the bottle's
currency) comes from your BI portfolio when it holds that wine, vintage and size, else from the LiveTrade market
for its LWIN18; a wine BI doesn't quote asks WineLabs.ai.

    python app/api/tasks/update_market_prices.py                 # dry run: how many API calls
    python app/api/tasks/update_market_prices.py --commit [--limit N]

Keys in the environment (.secrets.env): WINELABS_API_KEY, and the BI_
login (see bordeaux_index.py). Either one alone works.
price_bottle() also backs the bottle page's "Fetch market price" button in the app.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta

from sqlalchemy import create_engine, or_
from sqlalchemy.orm import sessionmaker

# app/api on the path (models, paths, tasks), for running this file as a script
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)
from tasks import USER_AGENT  # noqa: E402
from tasks.bordeaux_index import size_cl  # noqa: E402
from models import Bottle, Wine, WishlistItem  # noqa: E402

# Before the Settings page is saved: its defaults (app/api/settings.py), main currency EUR (1 unit = x euros)
MAIN_CURRENCY = "EUR"
EXCHANGE_RATES = {"EUR": 1.0, "USD": 0.92, "GBP": 1.17, "CHF": 1.05}

WINELABS_API_URL = "https://external-api.wine-labs.com/price_stats"
# A price from the last 90 days is kept: neither Bordeaux Index nor WineLabs is asked again for that bottle
# (the nightly script, the Maintenance task, and the other bottles of a wine whose market price button is clicked)
PRICE_MAX_AGE_DAYS = 90
# A price from fewer sales than this, way off the bottle's previous (or purchase) price, isn't saved: WineLabs has
# single mis-recorded sales (a Japanese wine at about 55,000 euros a bottle)
MIN_SALES = 3
MAX_JUMP = 5  # "way off": more than 5x, or less than a fifth


def _saved_settings(session):
    """The Settings page's values (app_settings), or {} without any."""
    if session is None:
        return {}
    try:
        from sqlalchemy import text
        # On a connection of its own: a failure here mustn't roll back the session's unsaved prices
        with session.get_bind().connect() as conn:
            row = conn.execute(text("SELECT data FROM app_settings ORDER BY id LIMIT 1")).first()
        return json.loads(row[0]) if row else {}
    except Exception:  # no such table
        return {}


def main_currency(session=None):
    """The main currency (Settings): a bottle without a currency is priced in it."""
    return (_saved_settings(session).get("currency") or MAIN_CURRENCY).upper()


def exchange_rates(session=None):
    """{currency: main currency per unit}: the Settings page's rates, else its defaults (never mixed: the defaults are
    in euros, saved rates in the saved main currency)."""
    saved = _saved_settings(session)
    if not saved.get("exchange_rates"):
        return dict(EXCHANGE_RATES)
    rates = {k.upper(): float(v) for k, v in saved["exchange_rates"].items()}
    rates[main_currency(session)] = 1.0
    return rates


def api_key():
    key = os.environ.get("WINELABS_API_KEY", "").strip()
    return key if key and key != "YOUR_API_KEY_HERE" else None


def bi_quotes(log=print, refresh=False):
    """{(LWIN7, vintage, size in cl): GBP per bottle} from the Bordeaux Index portfolio (the copy shared with the
    Cellar view, unless refresh), or {} without a BI login (or when BI can't be reached: then WineLabs)."""
    from tasks import bordeaux_index as bi
    if not bi.configured():
        return {}
    try:
        return bi.quotes([bi.line(it) for it in bi.cached_portfolio(refresh)[0]])
    except bi.BIError as e:
        log(f"  [WARN] Bordeaux Index: {e}; using WineLabs.ai only")
        return {}


def pricing_available():
    from tasks import bordeaux_index as bi
    return bool(api_key()) or bi.configured()


def bi_price(b, quotes, log, market=None):
    """The bottle's Bordeaux Index price in its own currency: from the portfolio `quotes`, else (with a `market`
    cache dict) the LiveTrade market; None when BI doesn't quote that wine."""
    from sqlalchemy.orm import object_session
    from tasks import bordeaux_index as bi
    wine = b.wine
    key = (str(wine.lwin), bi.vintage_key(wine.vintage), bi.size_cl(b.bottle_size))
    gbp = quotes.get(key) if quotes else None
    if not gbp and market is not None:
        if key not in market:
            try:
                market[key] = bi.market_quote(*key)
            except bi.BIError as e:
                log(f"  [WARN] Bordeaux Index market: {e}")
                market[key] = None
        gbp = market[key]
    if not gbp:
        return None
    currency = (b.currency or main_currency(object_session(b))).upper()
    if currency == "GBP":
        return gbp
    rates = exchange_rates(object_session(b))
    if "GBP" not in rates or currency not in rates:
        log(f"  [SKIP] No exchange rate for GBP or {currency}: add it on the Settings page")
        return None
    return gbp * rates["GBP"] / rates[currency]


def pick_price(stats):
    """WineLabs' own price, unless it falls outside the middle half of the sales (p25-p75): then the median.
    (Roulot Vireuils 2023: winelabs_price 89.99 against 7 sales with p25 97, median 251.)"""
    price, median = stats.get('winelabs_price'), stats.get('median_value')
    p25, p75 = stats.get('p25'), stats.get('p75')
    if price and median and p25 is not None and p75 is not None and not p25 <= price <= p75:
        return median
    return price or median


def fetch_winelabs(lwin, vintage, target_currency="GBP", log=print):
    """{"price", "currency", "sales"} from WineLabs.ai for an LWIN and vintage, or None."""
    key = api_key()
    if not key:
        log("  [ERROR] WINELABS_API_KEY isn't set.")
        return None
    # WineLabs may timeout or fail if "NV" is appended to the LWIN query
    query_str = f"{lwin} {vintage}" if vintage and str(vintage).upper() != "NV" else f"{lwin}"
    payload = {"user_id": key, "query": query_str, "region": "world", "currency": target_currency}
    # A User-Agent of our own: Cloudflare in front of WineLabs rejects urllib's default one (error 1010)
    req = urllib.request.Request(WINELABS_API_URL, data=json.dumps(payload).encode(), method="POST",
                                 headers={"Content-Type": "application/json",
                                          "User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            data = json.load(res)
    except urllib.error.HTTPError as e:
        if e.code in (400, 404):
            log("  [WARN] Wine not found on WineLabs.ai")
        else:
            log(f"  [ERROR] WineLabs API returned HTTP {e.code}")
        return None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        log(f"  [ERROR] Connection to WineLabs.ai failed: {e}")
        return None
    results = data.get('results', [])
    if not results:
        log("  [WARN] No pricing results found for this wine on WineLabs.ai")
        return None
    # The first result usually has the latest price stats
    first_res = results[0]
    price = pick_price(first_res)
    if not price:
        return None
    return {"price": price, "currency": first_res.get('currency', data.get('currency', target_currency)),
            "sales": first_res.get('count')}


def price_bottle(b, cache=None, log=print, bi=None, market=None):
    """Fetches and stores one bottle's market price (in its own currency, for its format): from Bordeaux Index when
    `bi` (see bi_quotes) holds the wine or, with a `market` cache dict, the LiveTrade market quotes it; else WineLabs. The price, or None when there's none or it's implausible
    (see MIN_SALES). Doesn't commit."""
    from sqlalchemy.orm import object_session
    wine = b.wine
    currency = (b.currency or main_currency(object_session(b))).upper()
    price = bi_price(b, bi, log, market)
    if price is not None:
        log(f"  → Bordeaux Index: {price:,.2f} {currency}")
        b.last_price = price
        b.last_price_date = datetime.now()
        b.last_price_source = "Bordeaux Index"
        return price
    if not api_key():
        log("  [SKIP] Not quoted by Bordeaux Index, and no WINELABS_API_KEY for WineLabs.ai")
        return None
    cache_key = (wine.lwin, wine.vintage, currency)
    if cache is not None and cache_key in cache:
        r = cache[cache_key]
        log("  → (Using cached API response)")
    else:
        r = fetch_winelabs(wine.lwin, wine.vintage, target_currency=currency, log=log)
        if cache is not None:
            cache[cache_key] = r
    if not r:
        return None
    price, api_currency = r["price"], r["currency"]
    # Converted with the Settings page's rates if the API ignored our currency param
    if api_currency and api_currency.upper() != currency:
        rates = exchange_rates(object_session(b))
        if api_currency.upper() not in rates or currency not in rates:
            log(f"  [SKIP] No exchange rate for {api_currency.upper()} or {currency}: add it on the Settings page")
            return None
        price = price * rates[api_currency.upper()] / rates[currency]
        log(f"  → Converted from {api_currency.upper()} to {currency}")
    # Quotes are for a 75cl bottle: a magnum ("150cl", "1.5l", "Magnum") is twice that
    multiplier = (size_cl(b.bottle_size) or 75) / 75
    if multiplier != 1.0:
        price *= multiplier
        log(f"  → Scaled by {multiplier}x for format: {b.bottle_size}")
    # Few sales and way off what we know: a mis-recorded sale, not a price
    reference = b.last_price or b.price
    sales = r.get("sales")
    if reference and sales is not None and sales < MIN_SALES and not reference / MAX_JUMP <= price <= reference * MAX_JUMP:
        plural = "s" if sales != 1 else ""
        log(f"  [SKIP] WineLabs says {price:,.2f} {currency} from {sales} sale{plural}, against "
            f"{reference:,.2f} {currency} before: not saved")
        return None
    log(f"  → Found Price: {price:,.2f} {currency}" + (f" ({sales} sales)" if sales is not None else ""))
    b.last_price = price
    b.last_price_date = datetime.now()
    b.last_price_source = "WineLabs.ai"
    return price


def stale_before(max_age_days=PRICE_MAX_AGE_DAYS):
    """The date before which a price is due again (priced on or after it: kept)."""
    return (datetime.now() - timedelta(days=max_age_days)).date()


def cellar_bottles(session, max_age_days=PRICE_MAX_AGE_DAYS):
    """Bottles in the cellar whose wine has an LWIN, dearest first: only those whose price is missing or more than
    max_age_days old (0: all of them)."""
    query = session.query(Bottle).join(Wine).filter(Bottle.qty > 0, Wine.lwin.isnot(None), Wine.lwin != "")
    if max_age_days:
        query = query.filter(or_(Bottle.last_price.is_(None), Bottle.last_price_date.is_(None),
                                 Bottle.last_price_date < stale_before(max_age_days)))
    return query.order_by(Bottle.price.desc().nullslast()).all()


def wishlist_items(session, max_age_days=PRICE_MAX_AGE_DAYS):
    """Wishlist entries whose wine has an LWIN, priced like bottles: those whose price is missing or older than
    max_age_days (0: all of them)."""
    query = session.query(WishlistItem).join(Wine).filter(Wine.lwin.isnot(None), Wine.lwin != "")
    if max_age_days:
        query = query.filter(or_(WishlistItem.last_price.is_(None), WishlistItem.last_price_date.is_(None),
                                 WishlistItem.last_price_date < stale_before(max_age_days)))
    return query.order_by(WishlistItem.id).all()


def refresh_prices(session, bottles, log=print):
    """Fetches and saves the market price of each bottle: Bordeaux Index first (one portfolio read), then one
    WineLabs call per wine, vintage and currency; commits as it goes. Shared by the nightly script and the app's
    Settings page. [(bottle, old price, new price or None)]."""
    from tasks import bordeaux_index as bi_api
    cache, done = {}, []
    bi = bi_quotes(log, refresh=True)  # a price run starts from a fresh portfolio
    market = {} if bi_api.configured() else None
    if bi:
        log(f"Bordeaux Index: {len(bi)} wines priced from your portfolio, the LiveTrade market for others")
    for b in bottles:
        log(f"{b.wine.producer.name} {b.wine.cuvee or ''} {b.wine.vintage} (LWIN {b.wine.lwin})".replace("  ", " "))
        old = b.last_price
        fresh = (b.wine.lwin, b.wine.vintage, (b.currency or main_currency(session)).upper()) not in cache
        done.append((b, old, price_bottle(b, cache, log=log, bi=bi, market=market)))
        session.commit()
        if fresh and b.last_price_source != "Bordeaux Index":
            time.sleep(0.5)  # WineLabs rate limiting
    return done


def main(commit=False, limit=None):
    import paths
    session = sessionmaker(bind=create_engine(paths.DB_URL))()
    try:
        # Bottles in the cellar with an LWIN whose price is missing or older than 90 days
        bottles = cellar_bottles(session) + wishlist_items(session)  # the wishlist's wines too
        if limit:
            bottles = bottles[:limit]
        unique_requests = {(b.wine.lwin, b.wine.vintage, b.currency) for b in bottles}
        print(f"[*] Found {len(bottles)} bottles with out of date price data with LWIN in the cellar.")
        print(f"[*] This corresponds to {len(unique_requests)} unique API calls to WineLabs.ai.")
        if not commit:
            print("\n⚠ DRY RUN: Skipped actual API requests.")
            print(f"  Run with --commit to execute the {len(unique_requests)} API calls and save prices.")
            return
        if not pricing_available():
            print("[!] Neither WINELABS_API_KEY nor a Bordeaux Index login is set: nothing can be priced.")
        done = refresh_prices(session, bottles)
        updated = sum(1 for _, _, p in done if p)
        failed = len(done) - updated
        from_bi = sum(1 for b, _, p in done if p and b.last_price_source == "Bordeaux Index")
        print(f"\n✓ Committed {updated} prices to database ({from_bi} from Bordeaux Index, {updated - from_bi} "
              f"from WineLabs.ai; {failed} without one).")
    except Exception as e:
        session.rollback()
        print(f"[ERROR] {e}")
    finally:
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update bottle market prices using WineLabs.ai API.")
    parser.add_argument("--commit", action="store_true", help="Commit prices to DB (dry-run by default)")
    parser.add_argument("--limit", type=int, default=None, help="Process only the first N bottles (for testing).")
    args = parser.parse_args()
    main(commit=args.commit, limit=args.limit)
