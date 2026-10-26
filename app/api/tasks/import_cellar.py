"""A cellar from a CSV: the export of another app (CellarTracker, Vivino) or your own spreadsheet. One row per wine,
with its bottles when it has a quantity or a location, and a tasting when it has a tasting date, rating or note. Run
from Settings › Maintenance (Import a cellar): a preview by producer to tick, then the ticked rows are added.

Columns are recognised by their header (CellarTracker's and Vivino's among others), else picked on the card:
producer, cuvée, vintage, colour (and a category: sparkling, sweet, fortified), grape, appellation, region, country,
quantity, location (and a bin), size, price, currency, purchase date, vendor, tasting date, rating, note.

What isn't there is created: producers (by name or alias, else new) and grapes. The grape column is a blend style
("Red Bordeaux Blend", CellarTracker's: the wine's blend) or the wine's grapes, the main first ("Grenache, Syrah 30%",
by name or alias; shares when given), set on a new wine only. Appellations are the reference
list's (by name or alias, the region's column tried too); one that isn't there is left empty and named in the summary.
A wine is the producer's wine of that vintage with the same cuvée (and colour, appellation when given), else a new
one. A bottle line or tasting already there (same wine, location, quantity, purchase date; same date and rating) is
left out, so importing the same file twice adds nothing. Ratings out of 5 (Vivino's stars) or 20 become out of 100.
"""
import re
from collections import defaultdict

from tasks.blends import blend_style, names_a_style
from tasks.import_scores import COLOURS, date_of, read, vintage_of  # noqa: F401  (read: for the task)
from tasks.matching import Producers, cuvee_key, is_rose, norm, same_wine
from models import Appellation, Bottle, Producer, Region, TastingNote, Varietal, Wine

FIELDS = ["producer", "cuvee", "vintage", "colour", "category", "grape", "appellation", "region", "country",
          "quantity", "location", "bin", "size", "price", "currency", "purchase_date", "vendor",
          "tasting_date", "rating", "note"]
REQUIRED = ["producer"]
# Headers that name a field (as norm() writes them), the preferred first: CellarTracker's Designation before its
# Wine (the whole name), Varietal before MasterVarietal
HEADERS = {
    "producer": ["producer", "winery", "producteur", "domaine", "estate", "maker", "chateau", "sortproducer"],
    "cuvee": ["cuvee", "designation", "wine name", "cuvee name", "label", "name", "vineyard", "wine"],
    "vintage": ["vintage", "year", "millesime", "annee", "annata"],
    "colour": ["colour", "color", "couleur", "wine type", "type", "style"],
    "category": ["category", "categorie", "wine category"],
    "grape": ["varietal", "grape", "grapes", "variety", "cepage", "cepages", "grape variety", "mastervarietal"],
    "appellation": ["appellation", "aoc", "aop", "doc", "docg", "ava", "denomination", "subregion"],
    "region": ["region", "wine region", "locale"],
    "country": ["country", "pays"],
    "quantity": ["quantity", "qty", "bottles", "count", "number of bottles", "nb bouteilles", "bouteilles"],
    "location": ["location", "storage", "cellar", "rack", "emplacement"],
    "bin": ["bin", "slot", "shelf", "position"],
    "size": ["size", "bottle size", "format", "volume"],
    "price": ["price", "cost", "purchase price", "prix", "price per bottle", "bottle price"],
    "currency": ["currency", "devise"],
    "purchase_date": ["purchase date", "purchasedate", "purchased", "date purchased", "acquired", "date d achat"],
    "vendor": ["store", "vendor", "merchant", "shop", "purchased from", "seller", "caviste"],
    "tasting_date": ["tasting date", "tastingdate", "date tasted", "tasted", "consumed", "drunk", "scan date",
                     "date de degustation"],
    "rating": ["rating", "my rating", "your rating", "my score", "score", "points", "note sur 100"],
    "note": ["tasting notes", "tastingnotes", "my notes", "your review", "review", "notes", "note", "comment",
             "comments", "personal note", "commentaire"],
}
SIZES = {"375ml": "37.5cl", "37 5cl": "37.5cl", "half": "37.5cl", "750ml": "75cl", "75cl": "75cl", "0 75l": "75cl",
         "1500ml": "150cl", "1 5l": "150cl", "150cl": "150cl", "magnum": "150cl", "3000ml": "300cl", "3l": "300cl",
         "300cl": "300cl", "double magnum": "300cl", "jeroboam": "300cl", "6000ml": "600cl", "6l": "600cl",
         "600cl": "600cl", "imperial": "600cl", "methuselah": "600cl"}
# Region names other apps use for the app's regions
REGION_NAMES = {"burgundy": "Bourgogne", "rhone valley": "Rhone", "loire valley": "Loire", "piedmont": "Piemonte",
                "tuscany": "Toscana", "south west france": "Sud-Ouest", "southwest": "Sud-Ouest", "south west": "Sud-Ouest",
                "languedoc roussillon": "Languedoc", "corse": "Corsica", "usa": "United States"}
NEW_WINE, YOURS = "new wine", "your wine"
SHARE = re.compile(r"\s*\(?(\d{1,3})(?:[.,]\d+)?\s*%\)?\s*")


def grapes_of(text):
    """(blend style or None, [(name, share or None)]) from a grape column: a style ("Red Bordeaux Blend") or grapes
    separated by commas, semicolons, slashes, "&", "+" or " and " ("Grenache 60%, Syrah 40%")."""
    if not (text or "").strip():
        return None, []
    if names_a_style(text):
        return blend_style(text), []
    out = []
    for part in re.split(r"[,;/&+]|\s-\s|\band\b|\bet\b", text):
        m = SHARE.search(part)
        share = int(m.group(1)) if m and 0 < int(m.group(1)) <= 100 else None
        name = " ".join(SHARE.sub(" ", part).split())
        if name:
            out.append((name, share))
    return None, out


def columns(headers):
    """{field: header}: for each field, the first of its HEADERS names among the headers."""
    keyed = {norm(h): h for h in reversed(headers)}  # the first header of a name wins
    out = {}
    for field, names in HEADERS.items():
        header = next((keyed[n] for n in names if n in keyed and keyed[n] not in out.values()), None)
        if header:
            out[field] = header
    return out


def colour_of(colour, category):
    """The app's type from a colour ("Red", "Rouge", "Red wine") and a category ("Sparkling", "Dessert"), or None."""
    def look(text):
        t = " ".join(w for w in norm(text).split() if w not in ("wine", "wines", "vin", "vino", "dry", "sec"))
        return COLOURS.get(t) if t else None
    base, kind = look(colour), look(category)
    if kind in ("Bubbles", "Bubbles Rose"):
        return "Bubbles Rose" if base == "Rose" or kind == "Bubbles Rose" else "Bubbles"
    if kind in ("Sweet", "Fortified"):
        return kind
    return base or kind


def size_of(text):
    t = norm(text)
    return SIZES.get(t) or SIZES.get(t.replace(" ", "")) or ("75cl" if not t else text.strip())


def month_first(values):
    """Whether the file's dates are month/day/year (CellarTracker's, American): yes when one can only be read so
    (3/25/2024), no when one can only be read day first (25/3/2024), else no."""
    for v in values:
        m = re.match(r"\s*(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})", v or "")
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if a > 12:
                return False
            if b > 12:
                return True
    return False


def day(text, us=False):
    """A date from "2024-03-01", "2024-03-01 20:15:00", "1/3/2024" (day first, or month first when `us`), "Mar
    2024"...; None when it's none."""
    from datetime import date, datetime
    t = (text or "").strip()
    if not t:
        return None
    try:
        return datetime.fromisoformat(t[:19]).date() if len(t) > 10 else date.fromisoformat(t[:10])
    except ValueError:
        pass
    m = re.fullmatch(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})", t.split()[0])
    if m:
        a, b, y = (int(x) for x in m.groups())
        y += 2000 if y < 100 else 0
        mo, d = (a, b) if us else (b, a)
        try:
            return date(y, mo, d)
        except ValueError:
            return None
    return date_of(t)


def number(text):
    """"1,250.00", "€45", "45,5" -> a float, else None."""
    t = re.sub(r"[^\d.,]", "", text or "")
    if not t:
        return None
    if "," in t and "." not in t and len(t.rsplit(",", 1)[1]) != 3:
        t = t.replace(",", ".")  # 45,5: a decimal comma
    try:
        return float(t.replace(",", ""))
    except ValueError:
        return None


class Lookup:
    """The database's producers, appellations, regions and grapes by name."""

    def __init__(self, session):
        self.producers = Producers(session.query(Producer).all())
        self.appellations = defaultdict(list)
        for a in session.query(Appellation).all():
            for key in {norm(n) for n in [a.name, *re.split(r"[,;]", a.aliases or "")]} - {""}:
                self.appellations[key].append(a)
        self.regions = {norm(r.name): r for r in session.query(Region).all() if r.name}
        self.grapes = {norm(v.name): v for v in session.query(Varietal).all() if v.name}
        for v in list(self.grapes.values()):
            for alias in re.split(r"[,;]", v.aliases or ""):
                self.grapes.setdefault(norm(alias), v)

    def region(self, *names):
        for name in names:
            key = norm(name)
            if not key:
                continue
            r = self.regions.get(key) or self.regions.get(norm(REGION_NAMES.get(key, "")))
            if r is None:  # "Loire Valley" -> Loire
                r = next((r for k, r in self.regions.items() if k and f" {k} " in f" {key} "), None)
            if r is not None:
                return r
        return None

    def appellation(self, name, region):
        found = self.appellations.get(norm(name), []) if norm(name) not in ("", "unknown", "n a") else []
        if len(found) > 1 and region is not None:
            found = [a for a in found if a.region_id == region.id] or found[:1]
        return found[0] if found else None


def plan(session, rows, mapping):
    """[{"line", "row", "outcome", "actions", ...}] per row: outcome "add" (a wine to create or find, bottles and a
    tasting to add) or why it's left out."""
    look = Lookup(session)
    ratings = [number(r.get(mapping.get("rating", ""), "")) for r in rows] if mapping.get("rating") else []
    top = max([x for x in ratings if x is not None] or [0])
    scale = 20 if 0 < top <= 5 else 5 if 5 < top <= 20 else 1  # stars, /20, /100
    wines = {}  # producer id -> its wines
    new_producers, new_wines = {}, {}  # name key -> line; wine key -> line
    seen_bottles, seen_tastings = set(), set()
    us = month_first([r.get(mapping.get(f, ""), "") for r in rows for f in ("purchase_date", "tasting_date")
                      if mapping.get(f)])
    out = []
    for n, raw in enumerate(rows, start=2):
        row = {f: (raw.get(mapping[f]) or "").strip() if mapping.get(f) else "" for f in FIELDS}
        item = {"line": n, "row": row, "actions": [], "doubts": []}
        out.append(item)
        if not row["producer"]:
            item["outcome"] = "no producer"
            continue
        vintage = vintage_of(row["vintage"]) if row["vintage"] else "NV"
        if vintage is None:
            item["outcome"] = f"vintage not understood: {row['vintage']}"
            continue
        producer, several = look.producers.named(row["producer"])
        if several:
            item["outcome"] = "producer ambiguous"
            item["fits"] = several
            continue
        if producer is not None and look.producers.how.endswith("distinctive words"):
            item["doubts"].append(f"producer taken for {producer.name} (by its distinctive words)")
        region = look.region(row["region"], row["country"])
        appellation = look.appellation(row["appellation"], region) or (
            look.appellation(row["region"], region) if not row["appellation"] else None)
        if row["appellation"] and appellation is None and norm(row["appellation"]) not in ("unknown", "n a"):
            item["unknown_appellation"] = row["appellation"]
        region = (appellation.region_obj if appellation is not None and appellation.region_id else None) or region
        blend, named = grapes_of(row["grape"])
        grapes = [(look.grapes.get(norm(name)), name, share) for name, share in named]  # (Varietal or None, ...)
        colour = colour_of(row["colour"], row["category"])
        cuvee = row["cuvee"]
        if colour == "Bubbles" and is_rose(cuvee):  # "Brut Rosé": a sparkling rosé
            colour = "Bubbles Rose"
        if mapping.get("cuvee") and norm(mapping["cuvee"]) == "wine":  # CellarTracker's whole name: the rest
            words = cuvee.split()
            for part in (row["producer"], appellation.name if appellation else row["appellation"]):
                pw = norm(part).split()
                ws = [norm(w) for w in words]
                if pw and ws[:len(pw)] == pw:
                    words = words[len(pw):]
            cuvee = " ".join(words)
        item.update(producer=producer, producer_name=producer.name if producer else " ".join(row["producer"].split()),
                    vintage=vintage, appellation=appellation, region=region, grapes=grapes, blend=blend,
                    colour=colour, cuvee=cuvee)
        if producer is None:
            key = norm(row["producer"])
            item["actions"].append("new producer" if key not in new_producers else "new producer (above)")
            new_producers.setdefault(key, n)
        for v, name, _ in grapes:
            if v is None:
                item["actions"].append(f"new grape {name}")
        # The wine: the producer's of that vintage with the same cuvée, colour and appellation when given
        key = cuvee_key(cuvee, None)
        wine = None
        if producer is not None:
            if producer.id not in wines:
                wines[producer.id] = session.query(Wine).filter(Wine.producer_id == producer.id).all()
            fits = [w for w in wines[producer.id]
                    if (w.vintage or "NV") == vintage and same_wine(cuvee_key(w.cuvee, None), key)
                    and (colour is None or w.type == colour)
                    and (appellation is None or w.appellation_id == appellation.id)]
            if len(fits) > 1:
                fits = [w for w in fits if norm(w.cuvee or "") == norm(cuvee)] or fits
            if len(fits) > 1:
                item["doubts"].append(f"{len(fits)} of your wines fit: the first is used")
            wine = fits[0] if fits else None
        item["wine"] = wine
        wkey = (norm(item["producer_name"]), vintage, key, colour, appellation and appellation.id)
        item["wine_key"] = wkey
        if wine is None:
            item["actions"].append(NEW_WINE if wkey not in new_wines else "new wine (above)")
            new_wines.setdefault(wkey, n)
        # Its bottles
        qty = number(row["quantity"])
        location = " ".join(x for x in (row["location"], row["bin"]) if x)
        if (qty or location) and (qty is None or qty > 0):
            qty = int(qty) if qty else 1
            price, purchased = number(row["price"]), day(row["purchase_date"], us)
            bkey = (wkey, location, qty, purchased, price)
            have = wine is not None and any(b.location == (location or None) and b.qty == qty
                                            and b.purchase_date == purchased for b in wine.inventory)
            if have or bkey in seen_bottles:
                item["actions"].append("bottles already there")
            else:
                seen_bottles.add(bkey)
                item["bottle"] = {"qty": qty, "location": location or None, "bottle_size": size_of(row["size"]),
                                  "price": price, "currency": (row["currency"] or "").upper() or None,
                                  "purchase_date": purchased, "vendor": row["vendor"] or None}
                item["actions"].append(f"{qty} bottle{'s' if qty > 1 else ''}" + (f" at {location}" if location else ""))
        # Its tasting
        rating = number(row["rating"])
        tasted = day(row["tasting_date"], us)
        if tasted or rating or row["note"]:
            rating = round(rating * scale) if rating else None
            tkey = (wkey, tasted, rating)
            have = wine is not None and any(t.date == tasted and t.rating == rating
                                            for b in wine.inventory for t in b.tastings)
            if have or tkey in seen_tastings:
                item["actions"].append("tasting already there")
            else:
                seen_tastings.add(tkey)
                item["tasting"] = {"date": tasted, "rating": rating, "notes": row["note"] or None}
                item["actions"].append("tasting" + (f" {tasted:%d %b %Y}" if tasted else "") + (f" ({rating})" if rating else ""))
        if wine is not None and not item.get("bottle") and not item.get("tasting"):
            item["outcome"] = "already there"
            continue
        item["outcome"] = "add"
    return out


def apply(session, items, main_currency="EUR", consumed="Consumed", ad_hoc="Ad-Hoc"):
    """Adds the planned rows: producers, grapes and wines as needed (once each), bottles, tastings (a tasting
    without bottles of its own gets a consumed one, as a tasting logged in the app). Counts."""
    counts = dict.fromkeys(["producers", "wines", "bottles", "tastings", "grapes"], 0)
    producers, grapes, wines = {}, {}, {}
    for it in items:
        producer = it["producer"]
        if producer is None:
            key = norm(it["producer_name"])
            if key not in producers:
                producers[key] = Producer(name=it["producer_name"], region_id=it["region"].id if it["region"] else None)
                session.add(producers[key])
                counts["producers"] += 1
            producer = producers[key]
        wine_grapes = []
        for v, name, share in it["grapes"]:
            if v is None:
                gkey = norm(name)
                if gkey not in grapes:
                    grapes[gkey] = Varietal(name=name)
                    session.add(grapes[gkey])
                    counts["grapes"] += 1
                v = grapes[gkey]
            wine_grapes.append((v, share))
        wine = it["wine"]
        if wine is None:
            if it["wine_key"] not in wines:
                wines[it["wine_key"]] = Wine(producer=producer, cuvee=it["cuvee"], vintage=it["vintage"],
                                             type=it["colour"], appellation=it["appellation"], blend=it["blend"],
                                             region_id=it["region"].id if it["region"] else None)
                wines[it["wine_key"]].set_grapes(wine_grapes)
                session.add(wines[it["wine_key"]])
                counts["wines"] += 1
            wine = wines[it["wine_key"]]
        bottle = None
        if it.get("bottle"):
            b = dict(it["bottle"])
            b["currency"] = b["currency"] or main_currency
            bottle = Bottle(wine=wine, **b)
            session.add(bottle)
            counts["bottles"] += 1
        if it.get("tasting"):
            if bottle is None:
                bottle = Bottle(wine=wine, qty=0, location=consumed, provenance=ad_hoc, currency=main_currency)
                session.add(bottle)
            session.add(TastingNote(bottle=bottle, **it["tasting"]))
            counts["tastings"] += 1
    return counts


def label(it):
    return f"{it.get('cuvee') or it['row'].get('cuvee') or '(plain)'} {it.get('vintage') or it['row'].get('vintage') or ''}".strip()
