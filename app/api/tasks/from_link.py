"""A wine from a shop's (or Vivino's) page: the page's product details (JSON-LD, Open Graph, its title) and its name
read into producer, cuvée, vintage, appellation and colour against the database. For the wine form's "Fill from a
link": a draft to check, nothing saved.
"""
import html
import json
import re
import urllib.error
import urllib.request
from datetime import date
from html.parser import HTMLParser

from tasks import USER_AGENT
from tasks.import_cellar import SIZES, Lookup
from tasks.import_scores import COLOURS
from tasks.match_lwin import producer_keys
from tasks.matching import cuvee_key, norm, same_wine

MAX_BYTES = 3_000_000
# Shop and site names after the wine's in a page title ("Clos Rougeard Le Bourg 2016 | Vivino")
TITLE_SPLIT = re.compile(r"\s+[|–—]\s+|\s+-\s+")
# Words around a wine's name that aren't part of it
NOISE = {"buy", "online", "wine", "bottle", "bottles", "price", "acheter", "vin", "case", "of", "x", "en", "primeur",
         "75cl", "750ml", "cl", "ml", "aoc", "aop", "doc", "docg", "igp", "vdf", "vivino"}


class LinkError(ValueError):
    """The page can't be read (address, network, not a page)."""


class _Page(HTMLParser):
    """The bits of a page that describe a product: its JSON-LD blocks, its meta tags, its title."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ld, self.meta, self.title = [], {}, ""
        self._in = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "script" and (a.get("type") or "").lower() == "application/ld+json":
            self._in, self._buf = "ld", []
        elif tag == "title":
            self._in, self._buf = "title", []
        elif tag == "meta":
            key = (a.get("property") or a.get("name") or a.get("itemprop") or "").lower()
            if key and a.get("content") and key not in self.meta:
                self.meta[key] = a["content"].strip()

    def handle_data(self, data):
        if self._in:
            self._buf.append(data)

    def handle_endtag(self, tag):
        if self._in == "ld" and tag == "script":
            self.ld.append("".join(self._buf))
            self._in = None
        elif self._in == "title" and tag == "title":
            self.title = " ".join("".join(self._buf).split())
            self._in = None


def public(url):
    """Whether the address is on the internet: not this machine, the local network or a link-local / reserved range
    (the NAS's own admin page, a router), as its host resolves now"""
    import ipaddress
    import socket
    from urllib.parse import urlsplit
    host = urlsplit(url).hostname
    if not host:
        return False
    try:
        addrs = {info[4][0] for info in socket.getaddrinfo(host, None)}
    except (socket.gaierror, UnicodeError):
        return True  # unknown here: the request fails as unreachable, as it would anyway
    for a in addrs:
        ip = ipaddress.ip_address(a.split("%")[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            return False
    return True


class _PublicOnly(urllib.request.HTTPRedirectHandler):
    """Each redirect checked too: a public page mustn't send the request on to the local network"""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not public(newurl):
            raise LinkError("That link leads to a local address")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url):
    """The page's HTML (a browser-like request; a few MB at most). Only on the internet: never this machine or the
    local network (a link, or a redirect, to the NAS's admin page)."""
    if not re.match(r"^https?://", url or "", re.I):
        raise LinkError("Paste a web address (https://…)")
    if not public(url):
        raise LinkError("That's a local address: only shops' pages on the internet can be read")
    req = urllib.request.Request(url, headers={"User-Agent": f"Mozilla/5.0 (compatible; {USER_AGENT})",
                                               "Accept": "text/html,application/xhtml+xml", "Accept-Language": "en,fr"})
    try:
        with urllib.request.build_opener(_PublicOnly).open(req, timeout=15) as r:
            if "html" not in (r.headers.get("Content-Type") or "html"):
                raise LinkError("That address isn't a web page")
            raw = r.read(MAX_BYTES)
            charset = r.headers.get_content_charset() or "utf-8"
    except urllib.error.HTTPError as e:
        raise LinkError(f"The shop answered with an error ({e.code}): it may not let apps read its pages") from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise LinkError(f"The page couldn't be reached ({getattr(e, 'reason', e)})") from e
    return raw.decode(charset, errors="replace")


def _products(blocks):
    """The JSON-LD objects of type Product (in lists and @graph too)."""
    out = []

    def walk(x):
        if isinstance(x, list):
            for y in x:
                walk(y)
        elif isinstance(x, dict):
            kind = x.get("@type")
            kinds = kind if isinstance(kind, list) else [kind]
            if any(str(k).lower() in ("product", "productgroup") for k in kinds):
                out.append(x)
            walk(x.get("@graph"))
    for b in blocks:
        try:
            walk(json.loads(b.strip()))
        except ValueError:
            continue
    return out


def _first(v):
    if isinstance(v, list):
        return _first(v[0]) if v else None
    if isinstance(v, dict):
        return v.get("url") or v.get("name") or v.get("@id")
    return v


def details(page_html, url=""):
    """{name, brand, image, price, currency, title} from a page: its product's JSON-LD first, then Open Graph and
    product meta tags, then the title."""
    p = _Page()
    p.feed(page_html)
    prod = next(iter(_products(p.ld)), {})
    offers = prod.get("offers") or {}
    offer = offers[0] if isinstance(offers, list) and offers else offers if isinstance(offers, dict) else {}
    if offer.get("@type") == "AggregateOffer" and not offer.get("price"):
        offer = {**offer, "price": offer.get("lowPrice")}
    m = p.meta
    name = prod.get("name") or m.get("og:title") or m.get("twitter:title") or p.title
    price = offer.get("price") or m.get("product:price:amount") or m.get("og:price:amount")
    try:
        price = float(str(price).replace(",", ".")) if price not in (None, "") else None
    except ValueError:
        price = None
    return {
        "name": html.unescape(str(name or "")).strip(),
        "brand": html.unescape(str(_first(prod.get("brand")) or "")).strip() or None,
        "image": _first(prod.get("image")) or m.get("og:image") or m.get("twitter:image"),
        "price": price,
        "currency": offer.get("priceCurrency") or m.get("product:price:currency") or m.get("og:price:currency"),
        "title": p.title,
        "url": url,
    }


def _clean_name(name):
    """The wine's part of a product name or page title: "Clos Rougeard Le Bourg 2016 | Vivino" -> the first part, or
    the part holding a vintage."""
    parts = [x for x in TITLE_SPLIT.split(name or "") if x.strip()]
    if not parts:
        return ""
    with_year = [x for x in parts if re.search(r"\b(19|20)\d\d\b|\bNV\b", x)]
    return (with_year or parts)[0].strip()


def read_name(name, lookup, brand=None):
    """{producer, cuvee, vintage, type, size, appellation, region} from a wine's name, against the database (a
    Lookup): what's found is a row ({id, name}), what isn't a name to create ({id: None, name})."""
    text = _clean_name(name)
    toks = norm(text).split()
    out = {"producer": None, "cuvee": "", "vintage": "", "type": None, "size": None, "appellation": None, "region": None}

    # The vintage: a year that can be one, or NV
    year = re.search(r"\b(19[0-9]{2}|20[0-9]{2})\b", text)
    if year and 1900 <= int(year.group(1)) <= date.today().year + 1:
        out["vintage"] = year.group(1)
    elif re.search(r"\b(nv|non[- ]vintage|sans annee)\b", text, re.I):
        out["vintage"] = "NV"

    # The producer: the shop's brand when it's one we know, else the longest known name the title starts with (after
    # a vintage some shops put first: "2016 Clos Rougeard, Saumur-Champigny, Bourg")
    producers = lookup.producers
    p = producers.exact(brand) if brand else None
    if p is None:
        lead = 1 if toks and re.fullmatch(r"(19|20)\d\d", toks[0]) else 0
        p, _ = producers.starting(toks[lead:])
    if p is not None:
        out["producer"] = {"id": p.id, "name": p.name}
        # its name's words are its, not the cuvée's, wherever they are ("Saumur-Champigny Clos Rougeard 2016")
        _remove_run(toks, [norm(k).split() for k in [p.name, *producer_keys(p.name)]])
    elif brand:
        out["producer"] = {"id": None, "name": brand}
        _remove_run(toks, [norm(brand).split()])

    # The appellation: the longest run of words that names one
    best = None
    for i in range(len(toks)):
        for j in range(len(toks), i, -1):
            key = " ".join(toks[i:j])
            if key in lookup.appellations and (best is None or j - i > best[1] - best[0]):
                best = (i, j, lookup.appellations[key][0])
                break
    if best:
        a = best[2]
        out["appellation"] = {"id": a.id, "name": a.name}
        if a.region_id:
            out["region"] = {"id": a.region_id, "name": a.region_obj.name if a.region_obj else None}
        del toks[best[0]:best[1]]

    # Colour and size words
    for k in sorted(COLOURS, key=lambda c: -len(c.split())):
        kt = k.split()
        for i in range(len(toks) - len(kt) + 1):
            if toks[i:i + len(kt)] == kt:
                out["type"] = out["type"] or COLOURS[k]
                if k not in ("champagne",):  # a colour word isn't the cuvée's ("Le Bourg Rouge"); Champagne may be
                    del toks[i:i + len(kt)]
                break
    for k, size in SIZES.items():
        kt = k.split()
        for i in range(len(toks) - len(kt) + 1):
            if toks[i:i + len(kt)] == kt:
                out["size"] = size
                del toks[i:i + len(kt)]
                break

    # The cuvée: what's left of the original words, in their own spelling
    rest = [t for t in toks if t != norm(out["vintage"]) and t not in NOISE and not re.fullmatch(r"\d+", t)]
    words = re.findall(r"[^\s,()]+", re.sub(r"\b(19|20)\d\d\b", " ", text))
    kept, want = [], list(rest)
    for w in words:
        nw = norm(w)
        if want and nw and nw.split()[0] == want[0]:
            kept.append(w.strip("'\"“”‘’"))
            want = want[len(nw.split()):]
    out["cuvee"] = " ".join(kept).strip(" -–")
    return out


def _remove_run(toks, runs):
    """Takes the first of these word runs found in toks out of it (the longest runs tried first)."""
    for run in sorted((r for r in runs if r), key=len, reverse=True):
        for i in range(len(toks) - len(run) + 1):
            if toks[i:i + len(run)] == run:
                del toks[i:i + len(run)]
                return


def known_cuvee(session, out):
    """The producer's cuvée in WineLib this wine is (same words, generic ones aside): its spelling, colour,
    appellation and region fill the draft ("Bourg" read as your "Le Bourg"); the same vintage there: `wine_id`."""
    from models import Wine
    pid = (out.get("producer") or {}).get("id")
    if not pid:
        return out
    appellation = (out.get("appellation") or {}).get("name")
    # With the appellation when the page names one; else the cuvée's words alone
    if appellation:
        target, key = cuvee_key(f"{out['cuvee']} {appellation}", None), (lambda w: cuvee_key(w.cuvee, w.appellation))
    else:
        target, key = cuvee_key(out["cuvee"], None), (lambda w: cuvee_key(w.cuvee, None))
    found = [w for w in session.query(Wine).filter(Wine.producer_id == pid).all()
             if target and same_wine(key(w), target) and (not out["type"] or w.type == out["type"])]
    if not found:
        return out
    by_vintage = sorted(found, key=lambda w: str(w.vintage or ""), reverse=True)
    same = next((w for w in found if out["vintage"] and str(w.vintage) == out["vintage"]), None)
    w = same or by_vintage[0]
    out["cuvee"] = w.cuvee or ""
    out["type"] = out["type"] or w.type
    if w.appellation:
        out["appellation"] = {"id": w.appellation.id, "name": w.appellation.name}
    if w.region_obj:
        out["region"] = {"id": w.region_obj.id, "name": w.region_obj.name}
    # what another vintage of it carries over, as the form's New vintage does
    out["grapes"] = [{"id": g.varietal_id, "name": g.varietal.name, "share": g.share} for g in w.grapes if g.varietal]
    out["blend"], out["lwin"] = w.blend or None, w.lwin or None
    out["wine_id"] = same.id if same else None
    out["like_id"] = w.id  # the vintage it was read against: a new vintage starts from it (vineyard and all)
    return out


def from_link(session, url):
    """The wine a page describes: its details and its name read against the database (and its known cuvée)."""
    d = details(fetch(url), url)
    if not d["name"]:
        raise LinkError("No wine found on that page")
    out = {**d, "wine_id": None, **read_name(d["name"], Lookup(session), d["brand"])}
    return known_cuvee(session, out)
