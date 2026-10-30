"""A purchase from a pasted text (an order or auction email, an invoice, a producer's sheet): the wine's line read
into producer, cuvée, vintage, appellation and colour against the database (as Fill from a link reads a page's
name), with the quantity, price, currency, date and vendor the text gives. For the bottle form's "Fill from text": a
draft to check, nothing saved.
"""
import re
from datetime import date

from sqlalchemy import func

from tasks.from_link import known_cuvee, read_name
from tasks.import_cellar import SIZES, Lookup

MAX_CHARS = 200_000
YEAR = re.compile(r"\b(19[0-9]{2}|20[0-9]{2})\b")
# "2 Bouteilles", "6 x", "1 btl", "3 magnums": the quantity just before a wine's name
QTY = re.compile(r"(?:^|\s)(\d{1,3})\s*(x|×|bouteilles?|bottles?|btls?|bts?|magnums?|jéroboams?|jeroboams?|cols?)(?:\s+|$)",
                 re.I)
CURRENCIES = {"€": "EUR", "eur": "EUR", "euros": "EUR", "$": "USD", "usd": "USD", "£": "GBP", "gbp": "GBP",
              "chf": "CHF", "sgd": "SGD", "s$": "SGD", "hk$": "HKD", "hkd": "HKD"}
_CUR = r"(€|eur|euros|usd|\$|£|gbp|chf|sgd|s\$|hk\$|hkd)"
_AMOUNT = r"(\d{1,3}(?:[ .  ]\d{3})*(?:,\d{1,2})?|\d+(?:[.,]\d{1,2})?)"
MONEY = re.compile(rf"{_AMOUNT}\s*{_CUR}(?![a-z])|{_CUR}\s*{_AMOUNT}", re.I)
# A price that is the whole lot's or order's, not a bottle's
TOTAL_WORDS = re.compile(r"total|adjudication|hammer|lot|montant|amount|subtotal|sous-total", re.I)
PRICE_WORDS = re.compile(r"prix|price|total|adjudication|hammer|montant|amount|unit", re.I)
MONTHS = {m: i for i, names in enumerate([
    ("january", "janvier", "jan"), ("february", "fevrier", "février", "feb", "fev", "fév"), ("march", "mars", "mar"),
    ("april", "avril", "apr", "avr"), ("may", "mai"), ("june", "juin", "jun"), ("july", "juillet", "jul", "juil"),
    ("august", "aout", "août", "aug"), ("september", "septembre", "sep", "sept"), ("october", "octobre", "oct"),
    ("november", "novembre", "nov"), ("december", "decembre", "décembre", "dec", "déc")], 1) for m in names}


def _amount(s):
    s = s.replace(" ", " ").replace(" ", " ").strip()
    if re.search(r",\d{1,2}$", s):  # 1.234,50 or 680,00: the comma is the decimal one
        s = s.replace(".", "").replace(" ", "").replace(",", ".")
    else:
        s = s.replace(",", "").replace(" ", "")
    try:
        return float(s)
    except ValueError:
        return None


def _segments(text):
    """The text cut where a wine's name can't run on: lines, table cells, labels ("Couleur :"), sentences."""
    for line in re.split(r"[\r\n|•●]+", text):
        for part in re.split(r"\s+:\s+|\s{3,}|\.\s+(?=[A-Z])", line):
            if part.strip():
                yield part.strip()


def _wine_line(text, lookup):
    """(the reading of the line most likely the wine's, its quantity): a line with a vintage, a known producer
    first, then the most it names (appellation, cuvée)."""
    best, best_score = None, -1
    for seg in _segments(text):
        y = YEAR.search(seg)
        if not y or len(seg) > 200:
            continue
        qty, unit = None, None
        m = QTY.search(seg)
        if m and (m.start() < y.start() or y.start() == 0):  # before the name, or the vintage leads ("2016 Clos...")
            qty, unit, seg = int(m.group(1)), m.group(2).lower().rstrip("s").replace("é", "e"), seg[m.end():]
        # the name ends at its vintage when the vintage comes after it ("Château Latour ... 1986 Couleur")
        y = YEAR.search(seg)
        if y and y.start() > 0:
            seg = seg[:y.end()]
        r = read_name(seg, lookup)
        if not r["vintage"]:
            continue
        p = r["producer"] or {}
        score = (4 if p.get("id") else 1 if p.get("name") else 0) + (2 if r["appellation"] else 0) + (1 if r["cuvee"] else 0)
        if score > best_score:
            best, best_score = ({**r, "line": seg, "size": r["size"] or SIZES.get(unit)}, qty), score
    return best


def _price(text, qty):
    """(price a bottle, currency, the text's own amount, whether it was a total): the first amount said to be a price
    (else the first amount); a lot's or order's total divided by the quantity."""
    found = []
    for line in re.split(r"[\r\n]+", text):
        for m in MONEY.finditer(line):
            amount = _amount(m.group(1) or m.group(4))
            cur = CURRENCIES.get((m.group(2) or m.group(3) or "").lower())
            if amount:
                found.append((amount, cur, line))
    if not found:
        return None, None, None, False
    amount, cur, line = next((f for f in found if PRICE_WORDS.search(f[2])), found[0])
    total = bool(qty and qty > 1 and TOTAL_WORDS.search(line))
    return (round(amount / qty, 2) if total else amount), cur, amount, total


def _date(text):
    """The first date in the text (dd/mm/yyyy, yyyy-mm-dd, "29 octobre 2026", "October 29, 2026"), as ISO."""
    candidates = []
    for m in re.finditer(r"\b(\d{1,2})[/.](\d{1,2})[/.](20\d{2})\b", text):
        candidates.append((m.start(), int(m.group(3)), int(m.group(2)), int(m.group(1))))
    for m in re.finditer(r"\b(20\d{2})-(\d{2})-(\d{2})\b", text):
        candidates.append((m.start(), int(m.group(1)), int(m.group(2)), int(m.group(3))))
    for m in re.finditer(r"\b(\d{1,2})(?:er)?\s+([a-zéû]+)\.?\s+(20\d{2})\b", text, re.I):
        if m.group(2).lower() in MONTHS:
            candidates.append((m.start(), int(m.group(3)), MONTHS[m.group(2).lower()], int(m.group(1))))
    for m in re.finditer(r"\b([A-Za-z]+)\.?\s+(\d{1,2}),?\s+(20\d{2})\b", text):
        if m.group(1).lower() in MONTHS:
            candidates.append((m.start(), int(m.group(3)), MONTHS[m.group(1).lower()], int(m.group(2))))
    for _, y, mo, d in sorted(candidates):
        try:
            when = date(y, mo, d)
        except ValueError:
            continue
        if when <= date.today():
            return when.isoformat()
    return None


def _vendor(session, text):
    """A vendor you've bought from before (or have a buyer's premium for) the text names."""
    import settings
    from models import Bottle
    names = {v for (v,) in session.query(Bottle.vendor).filter(Bottle.vendor.isnot(None)).distinct() if v and v.strip()}
    names |= set(settings.current.vendor_premiums)
    folded = re.sub(r"[^a-z0-9]+", " ", text.lower())
    for name in sorted(names, key=len, reverse=True):
        key = re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()
        if len(key) >= 3 and re.search(rf"\b{re.escape(key)}\b", folded):
            return name.strip()
    return None


def _labelled_appellation(text, lookup):
    """{appellation, region} from an "Appellation : Pauillac" label elsewhere in the text, or None."""
    from tasks.matching import norm
    for m in re.finditer(r"\bappellation\b\s*:?\s*([^\n|]{2,80})", text, re.I):
        toks = norm(m.group(1)).split()
        for j in range(len(toks), 0, -1):  # the longest run of the label's first words that names one
            hit = lookup.appellations.get(" ".join(toks[:j]))
            if hit:
                a = hit[0]
                return {"appellation": {"id": a.id, "name": a.name},
                        "region": {"id": a.region_id, "name": a.region_obj.name} if a.region_obj else None}
    return None


def from_text(session, text):
    """{producer, cuvee, vintage, type, size, appellation, region, grapes..., wine_id, like_id, line, qty, price,
    currency, price_total, purchase_date, vendor}: what the text says about a purchase, against the database."""
    text = (text or "")[:MAX_CHARS]
    lookup = Lookup(session)
    found = _wine_line(text, lookup)
    if found is None:
        raise ValueError("No wine with a vintage found in that text")
    out, qty = found
    if not out["appellation"]:
        out = {**out, **(_labelled_appellation(text, lookup) or {})}
    out = known_cuvee(session, {**out, "wine_id": None, "like_id": None})
    price, currency, as_written, total = _price(text, qty)
    return {**out, "qty": qty, "price": price, "currency": currency,
            "price_total": as_written if total else None, "purchase_date": _date(text), "vendor": _vendor(session, text)}
