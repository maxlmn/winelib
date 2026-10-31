"""Maintenance tasks for the Settings page: the scripts in app/api/tasks/, run as background jobs (see jobs.py).

Tasks that change data have a preview (dry run) first. Reports only read.
"""
import io
import os
import zipfile

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, sessionmaker

import jobs
import settings
import paths
from tasks.update_market_prices import PRICE_MAX_AGE_DAYS
from db import get_session

router = APIRouter()

# Database dumps and CSV folders from the backup task
BACKUP_DIR = paths.BACKUP_DIR
MAX_ITEMS = jobs.MAX_ITEMS


def _n(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


def _item(label, detail=None, href=None, **extra):
    return {"label": label, "detail": detail, "href": href, **extra}


# --- Tasks: fn(session, job) -> {"summary", "items"} ------------------------------------------------------


def _copy(session, wine_id, keep):
    """One copy of a duplicate wine, as the preview shows it: its page, and what it holds (bottles and where, tastings,
    scores, LWIN, vineyard), so you can tell the copies apart"""
    from sqlalchemy import func
    from models import Bottle, TastingNote, Wine
    w = session.get(Wine, wine_id)
    bottles = session.query(Bottle).filter(Bottle.wine_id == wine_id).all()
    here = sum(b.qty or 0 for b in bottles)
    places = sorted({b.location for b in bottles if b.qty and b.location})
    tasted = (session.query(func.count(TastingNote.id)).join(Bottle, TastingNote.bottle_id == Bottle.id)
              .filter(Bottle.wine_id == wine_id).scalar())
    scores = [f"{c.critic} {c.score}" for c in w.scores if c.score and c.score != "-"]
    facts = [f"{_n(here, 'bottle')} in {', '.join(places)}" if here else None,
             _n(tasted, "tasting") if tasted else None,
             ", ".join(scores) or None,
             f"LWIN {w.lwin}" if w.lwin else None,
             f"vineyard {w.vineyard.name}" if w.vineyard else None]
    return {"href": f"/wines/{wine_id}", "keep": keep,
            "facts": " · ".join(f for f in facts if f) or "nothing recorded on it"}


def _duplicates(session, job):
    from tasks import consolidate_duplicate_wines as dup
    groups = dup.find_duplicate_groups(session)
    # each group: the wine, then each of its copies (the one kept, the ones merged into it) with what it holds
    items = [_item(g["label"], href=f"/wines/{g['primary']}",
                   copies=[_copy(session, g["primary"], True)] + [_copy(session, d, False) for d in g["duplicates"]])
             for g in groups[:MAX_ITEMS]]
    dropped = sum(len(g["duplicates"]) for g in groups)
    if not job.commit:
        dup.describe(groups, log=job.log)
        if not groups:
            return {"summary": "No wine entered more than once.", "items": []}
        return {"summary": f"{_n(len(groups), 'wine')} entered more than once: merging gathers each one's bottles and "
                           f"tastings on the copy kept, and deletes {'the other copy' if dropped == 1 else f'the {dropped} others'}.",
                "items": items}
    try:
        moved = dup.merge_groups(session, groups, log=job.log)
    except ValueError as e:
        raise RuntimeError(str(e))
    return {"summary": f"{_n(moved, 'cellar line')} moved into {_n(len(groups), 'wine')}, "
                       f"{_n(dropped, 'duplicate')} deleted.", "items": items}


def _orphans(session, job):
    from tasks.housekeeping.check_orphans import find_orphans
    r = find_orphans(session)
    items = ([_item(f"Tasting note {n} has no bottle (bottle {b})", (t or "")[:120]) for n, b, t in r["notes"]] +
             [_item(f"Bottle {b} has no wine (wine {w})", loc) for b, w, loc in r["bottles"]])
    t = r["totals"]
    job.log(f"{t['wines']} wines, {t['cellar']} bottles, {t['tasting_notes']} tasting notes")
    return {"summary": f"{len(r['notes'])} notes without a bottle, {len(r['bottles'])} bottles without a wine "
                       f"(of {t['tasting_notes']} notes, {t['cellar']} bottles).", "items": items[:MAX_ITEMS]}


def _appellations_apart(session, job):
    """Cuvées filed under several appellations (tasks/vintages.py): a report, the likely duplicates first."""
    from tasks import vintages
    found = vintages.appellations_apart(session)
    items = []
    for c in found:
        w = c["wine"]
        apart = " · ".join(f"{a}: {', '.join(v)}" for a, v in c["by"])
        twice = f" (under two: {', '.join(c['both'])})" if c["both"] else ""
        items.append(_item(f"{w.producer.name} {w.cuvee}{twice}", apart, f"/wines/{w.id}"))
    both = sum(1 for c in found if c["both"])
    return {"summary": f"{_n(len(found), 'cuvée')} under more than one appellation; {both} with a vintage under two "
                       f"(probably entered twice: set one's appellation like the other's, then Duplicate wines "
                       f"merges them).", "items": items[:MAX_ITEMS]}


def _offer(task, a, b, wines_a, wines_b, keep_a, keep_b):
    """A pair the page can merge: keep a or b, the pick posted to `task` (merge_cuvees, merge_producers)."""
    return {"task": task, "a": a, "b": b, "wines": [wines_a, wines_b], "pick": {"a": keep_a, "b": keep_b}}


def _similar(session, job):
    from tasks.housekeeping.find_similar_cuvees import find_similar
    pairs = find_similar(session)
    # Each pair can be merged from the page (task merge_cuvees): keep one name, the other merges into it
    items = [_item(f"{p['producer']}: “{p['a'][0]}” / “{p['b'][0]}”", p["reason"], f"/producers/{p['producer_id']}",
                   merge=_offer("merge_cuvees", p["a"][0], p["b"][0], len(p["a"][1]), len(p["b"][1]),
                                {"producer_id": p["producer_id"], "keep": p["a"][0], "drop": p["b"][0]},
                                {"producer_id": p["producer_id"], "keep": p["b"][0], "drop": p["a"][0]}))
             for p in pairs[:MAX_ITEMS]]
    return {"summary": f"{_n(len(pairs), 'pair')} of cuvée names that may be the same cuvée.", "items": items}


def _merge_cuvees(session, job):
    """The pairs picked in the similar cuvée names report: [{"producer_id", "keep", "drop"}]. Each merge is
    checked for orphans; a preview rolls everything back."""
    from tasks.merge_cuvees import merge_cuvee
    pairs = job.params.get("pairs") or []
    items, totals = [], {"renamed": 0, "merged": 0, "lines_moved": 0}
    for p in pairs:
        job.log(f"{p['drop']} → {p['keep']} (producer {p['producer_id']})")
        try:
            r = merge_cuvee(session, int(p["producer_id"]), p["drop"], p["keep"], log=lambda line: job.log("  " + line))
        except ValueError as e:
            session.rollback()
            raise RuntimeError(f"“{p['drop']}” → “{p['keep']}”: {e}")
        for k in totals:
            totals[k] += r[k]
        items.append(_item(f"“{p['drop']}” → “{p['keep']}”",
                           f"{_n(r['renamed'], 'wine')} renamed, {_n(r['merged'], 'wine')} merged "
                           f"({_n(r['lines_moved'], 'cellar line')} moved)", f"/producers/{p['producer_id']}"))
    if job.commit:
        session.commit()
    else:
        session.rollback()
    verb = "" if job.commit else "would be "
    return {"summary": f"{_n(len(pairs), 'pair')}: {_n(totals['renamed'], 'wine')} {verb}renamed, "
                       f"{_n(totals['merged'], 'wine')} {verb}merged into their twin "
                       f"({_n(totals['lines_moved'], 'cellar line')} {verb}moved), no orphans.", "items": items}


def _similar_producers(session, job):
    from tasks.merge_producers import find_similar_producers
    pairs = find_similar_producers(session)
    items = [_item(f"“{p['a'][1]}” / “{p['b'][1]}”", p["reason"], f"/producers/{p['a'][0]}",
                   merge=_offer("merge_producers", p["a"][1], p["b"][1], p["a"][2], p["b"][2],
                                {"keep": p["a"][0], "drop": p["b"][0]}, {"keep": p["b"][0], "drop": p["a"][0]}))
             for p in pairs[:MAX_ITEMS]]
    return {"summary": f"{_n(len(pairs), 'pair')} of producers that may be one producer entered twice.",
            "items": items}


def _merge_producers(session, job):
    """The pairs picked in the duplicate producers report: [{"keep": id, "drop": id}]; a preview rolls back."""
    from tasks.merge_producers import merge_producer
    pairs = job.params.get("pairs") or []
    items, totals = [], {"moved": 0, "merged": 0, "lines_moved": 0}
    for p in pairs:
        try:
            r = merge_producer(session, int(p["keep"]), int(p["drop"]), log=job.log)
        except ValueError as e:
            session.rollback()
            raise RuntimeError(f"producer {p['drop']} → {p['keep']}: {e}")
        for k in totals:
            totals[k] += r[k]
        items.append(_item(f"producer {p['drop']} → {p['keep']}",
                           f"{_n(r['moved'], 'wine')} moved, {_n(r['merged'], 'wine')} merged into the same wine"
                           + (f", took {', '.join(r['filled'])}" if r["filled"] else ""), f"/producers/{p['keep']}"))
    if job.commit:
        session.commit()
    else:
        session.rollback()
    verb = "" if job.commit else "would be "
    return {"summary": f"{_n(len(pairs), 'producer')} {verb}merged: {_n(totals['moved'], 'wine')} {verb}moved, "
                       f"{_n(totals['merged'], 'wine')} {verb}merged into the same wine "
                       f"({_n(totals['lines_moved'], 'cellar line')} {verb}moved), no orphans.", "items": items}


def _csv(job, module):
    """An uploaded CSV's (headers, rows, mapping, columns): the columns as picked on the card, else as recognised by
    their header (`module`: import_scores or import_cellar, their read / columns / FIELDS / REQUIRED)"""
    headers, rows = module.read(job.params.get("_text") or "")
    if not rows:
        raise RuntimeError("No rows in this file (a CSV with a header line)")
    mapping = {f: h for f, h in (job.params.get("mapping") or module.columns(headers)).items() if h in headers}
    return headers, rows, mapping, {"headers": headers, "mapping": mapping, "fields": module.FIELDS, "required": module.REQUIRED}


def _outcomes(job, rows, mapping, results):
    """What became of each row, counted and logged"""
    from collections import Counter
    job.log(f"{_n(len(rows), 'row')}, columns: " + ", ".join(f"{f} = {h}" for f, h in mapping.items()))
    outcomes = Counter(it["outcome"] for it in results)
    for outcome, n in outcomes.most_common():
        job.log(f"{outcome}: {n}")
    return outcomes


def _unknown_producers(session, results, outcomes, label):
    """The producers not recognised (their rows' `outcome` in outcomes), by name: how many rows, a few examples, and
    which of yours could be meant (an alias then says which)"""
    from db import Producer
    ids = dict(session.query(Producer.name, Producer.id).all())
    unknown = {}
    for it in results:
        if it["outcome"] not in outcomes:
            continue
        name = it["row"]["producer"]
        g = unknown.setdefault(name.lower(), {"alias": name, "reviews": 0, "examples": [], "fits": []})
        g["reviews"] += 1
        if len(g["examples"]) < 3:
            g["examples"].append(label(it))
        g["fits"] = g["fits"] or [{"id": ids[n], "name": n} for n in it.get("fits", []) if n in ids]
    return list(unknown.values())


def _scores_csv(session, job):
    """Critics' scores from an uploaded CSV (app/api/tasks/import_scores.py), for the critic named on the card: a
    preview lists the rows by producer to tick (new wines, scores for wines you have), a run saves the ticked ones
    (params "keys": their line numbers)."""
    from collections import Counter
    from tasks import import_scores as sc
    critic = " ".join((job.params.get("critic") or "").split())
    headers, rows, mapping, columns = _csv(job, sc)
    missing = [f for f in sc.REQUIRED if f not in mapping]
    if missing or not ({"score", "note"} & set(mapping)):
        need = missing + ([] if {"score", "note"} & set(mapping) else ["score or note"])
        return {"summary": f"{_n(len(rows), 'row')}: pick the column for {', '.join(need)} below, then Preview again.",
                "items": [], "columns": columns}
    results = sc.plan(session, critic, rows, mapping)
    outcomes = _outcomes(job, rows, mapping, results)
    saving = (sc.ADD, sc.FILL, sc.REPLACE)
    if job.commit:
        keys = set(job.params.get("keys") or [])
        counts = sc.apply(session, critic, [it for it in results if it["outcome"] in saving and str(it["line"]) in keys])
        session.commit()
        settings.adopt_critic(session, critic)
        return {"summary": f"{critic}: {_n(counts[sc.ADD], 'wine')} added, {_n(counts[sc.FILL], 'score')} given to "
                           f"wines you have, {counts[sc.REPLACE]} replaced.", "items": []}
    items = []
    for it in results:
        if it["outcome"] not in saving:
            continue
        row, p = it["row"], it["producer"]
        doubt = it["matched_by"].endswith("distinctive words")  # not its name or an alias: to check
        what = {sc.ADD: "new wine", sc.FILL: "your wine, no score yet",
                sc.REPLACE: f"your wine, {critic} {it.get('current')} now"}[it["outcome"]]
        detail = " · ".join(x for x in (
            what, it["appellation"].name if it["appellation"] else None, it["colour"], it["grape"].name if it["grape"] else None,
            f"→ {row['score']}" if row["score"] else "note only", f"line {it['line']}",
            "check: producer found by its distinctive words" if doubt else None) if x)
        items.append(_item(sc.label(it), detail, row["link"] or None,
                           pick={"key": str(it["line"]), "group": p.name, "on": it["outcome"] != sc.REPLACE and not doubt,
                                 "flag": it["outcome"] == sc.FILL}))
    # Producers not recognised: the name to give one of yours as an alias
    unknown = _unknown_producers(session, results, ("producer not in the database", "producer ambiguous"), sc.label)
    unknown = sorted(unknown, key=lambda g: (-bool(g["fits"]), -g["reviews"], g["alias"].lower()))[:MAX_ITEMS]
    # Why the others are left out, the names not recognised first ("appellation not in the database: Ermitage")
    skipped = Counter(o.split(":")[0] for o in outcomes.elements() if o not in saving)
    names = Counter(o.split(": ", 1)[1] for o in outcomes.elements()
                    if o.startswith(("appellation not", "grape not", "colour not")))
    session.rollback()
    return {"summary": f"{critic}: {_n(outcomes[sc.ADD], 'wine')} to add, {_n(outcomes[sc.FILL], 'score')} for wines you "
                       f"have without one, {outcomes[sc.REPLACE]} replacing a different {critic} score, from "
                       f"{_n(len(rows), 'row')}." + (f" Left out: {', '.join(f'{o}: {n}' for o, n in skipped.most_common())}."
                                                     if skipped else "")
                       + (f" Not recognised: {', '.join(f'{x} ({n})' for x, n in names.most_common(12))}." if names else ""),
            "items": items, "flag": "scores for wines you have", "unknown": unknown, "columns": columns}


def _cellar_csv(session, job):
    """A cellar from an uploaded CSV (app/api/tasks/import_cellar.py): a preview lists the rows by producer to tick
    (wines found or new, bottles, tastings), a run adds the ticked ones (params "keys": their line numbers)."""
    from collections import Counter
    from tasks import import_cellar as ic
    from routers.forms import AD_HOC, CONSUMED
    headers, rows, mapping, columns = _csv(job, ic)
    if "producer" not in mapping:
        return {"summary": f"{_n(len(rows), 'row')}: pick the column for producer below, then Preview again.",
                "items": [], "columns": columns}
    results = ic.plan(session, rows, mapping)
    outcomes = _outcomes(job, rows, mapping, results)
    if job.commit:
        keys = set(job.params.get("keys") or [])
        counts = ic.apply(session, [it for it in results if it["outcome"] == "add" and str(it["line"]) in keys],
                          settings.current.currency, CONSUMED, AD_HOC)
        session.commit()
        return {"summary": "Added " + ", ".join(f"{_n(n, k[:-1])}" for k, n in counts.items() if n) + "."
                           if any(counts.values()) else "Nothing added.", "items": []}
    items = []
    for it in results:
        if it["outcome"] != "add":
            continue
        detail = " · ".join(x for x in (
            it["appellation"].name if it["appellation"] else None, it["colour"],
            ", ".join((v.name if v else n) + (f" {s}%" if s else "") for v, n, s in it["grapes"]) or it["blend"],
            ", ".join(it["actions"]), f"line {it['line']}",
            *(f"check: {d}" for d in it["doubts"])) if x)
        items.append(_item(ic.label(it), detail, f"/wines/{it['wine'].id}" if it["wine"] is not None else None,
                           pick={"key": str(it["line"]), "group": it["producer_name"], "on": not it["doubts"],
                                 "flag": it["wine"] is not None}))
    # Producers several of yours fit: an alias says which (the others are created when they don't exist)
    unknown = _unknown_producers(session, results, ("producer ambiguous",), ic.label)
    adds = [it for it in results if it["outcome"] == "add"]
    new_producers = {it["producer_name"].lower() for it in adds if it["producer"] is None}
    new_wines = {it["wine_key"] for it in adds if it["wine"] is None}
    skipped = Counter(o.split(":")[0] for o in outcomes.elements() if o != "add")
    unknown_apps = Counter(it["unknown_appellation"] for it in adds if it.get("unknown_appellation"))
    session.rollback()
    return {"summary": f"{_n(len(adds), 'row')} to add of {len(rows)}: {_n(len(new_producers), 'new producer')}, "
                       f"{_n(len(new_wines), 'new wine')}, {sum(1 for it in adds if it.get('bottle'))} bottle lines, "
                       f"{_n(sum(1 for it in adds if it.get('tasting')), 'tasting')}."
                       + (f" Left out: {', '.join(f'{o}: {n}' for o, n in skipped.most_common())}." if skipped else "")
                       + (f" Appellations not recognised (left empty): "
                          f"{', '.join(f'{a} ({n})' for a, n in unknown_apps.most_common(12))}." if unknown_apps else ""),
            "items": items, "flag": "your wines", "unknown": sorted(unknown, key=lambda g: -g["reviews"]),
            "columns": columns}


def _places(session, job):
    from tasks.geocode import fill_missing, missing, place_query
    limit = job.params.get("limit") or 10
    total = len(missing(session))
    found = fill_missing(session, limit=limit, commit=job.commit, log=job.log)
    hits = sum(1 for _, h in found if h)
    items = [_item(place_query(p), (h["address"][:120] if h else "no match: use Search OpenStreetMap or a Google "
                                    "Maps link in the place form"), f"/places/{p.id}") for p, h in found]
    verb = "saved" if job.commit else "found"
    return {"summary": f"{_n(total, 'place')} without coordinates; {hits} of {len(found)} looked up {verb} on "
                       f"OpenStreetMap.", "items": items}


def _kind(match):
    return match.lower().replace("(", "").replace(")", "")  # "FUZZY (91%)" -> "fuzzy 91%"


def _lwin(session, job):
    from tasks import match_lwin
    try:
        results = match_lwin.fill_missing_lwin(session, commit=job.commit, log=job.log)
    except FileNotFoundError:
        raise RuntimeError("No LWIN list on the server: build it with match_lwin.py --build-index and copy data/lwin/ "
                           "next to the app's database")
    count = {k: sum(1 for _, s, _ in results if s == k) for k in ("saved", "sure", "check", "none")}
    order = {"check": 0, "sure": 1, "saved": 1, "none": 2}
    items = []
    for w, status, found in sorted(results, key=lambda r: order[r[1]]):
        label = " ".join(x for x in (w.producer.name, w.cuvee or "", w.appellation.name if w.appellation else "",
                                     w.vintage or "") if x)
        if status in ("sure", "saved"):
            e, kind, _ = found[0]
            what = "like another vintage" if kind == "VINTAGE" else f"{e['display_name']} ({_kind(kind)})"
            detail = f"{'Saved' if status == 'saved' else 'Will save'} {e['lwin']}: {what}"
        elif status == "check":
            detail = "To check in the wine form: " + "; ".join(f"{e['lwin']} {e['display_name']} ({_kind(k)})"
                                                                 for e, k, _ in found)
        else:
            detail = "No match in the Liv-ex list"
        items.append(_item(label, detail, f"/wines/{w.id}"))
    sure = count["saved"] if job.commit else count["sure"]
    # An LWIN is the wine's, whatever the vintage: the run gives the saved ones to their other vintages (as the
    # wine form does)
    spread = len(match_lwin.spread_lwin(session, commit=True, log=job.log)[0]) if job.commit else 0
    return {"summary": f"{_n(len(results), 'cellar wine')} without an LWIN: {sure} "
                       f"{'saved' if job.commit else 'sure matches to save'}, {count['check']} to check by hand "
                       f"(Suggest in the wine form), {count['none']} not in the Liv-ex list."
                       + (f" {_n(spread, 'other vintage')} given the same LWIN." if spread else ""),
            "items": items[:MAX_ITEMS]}


def _prices(session, job, force=False):
    """force: every cellar bottle with an LWIN, however recent its price; else not those priced in the last 90 days."""
    from tasks import update_market_prices as prices
    bottles = prices.cellar_bottles(session, max_age_days=0 if force else prices.PRICE_MAX_AGE_DAYS)
    scope = "" if force else f" not priced in {prices.PRICE_MAX_AGE_DAYS} days"

    def link(b):
        return f"/bottles/{b.id}"

    def label(b):
        return " ".join(x for x in (b.wine.producer.name, b.wine.cuvee or "", b.wine.vintage or "") if x)

    def money(v, b):
        return f"{v:,.0f} {(b.currency or settings.current.currency).upper()}"

    if not job.commit:
        # Bordeaux Index prices the wines in your BI portfolio; WineLabs is asked for the rest
        bi = prices.bi_quotes(log=job.log)
        from_bi = [b for b in bottles if prices.bi_price(b, bi, lambda line: None) is not None]
        rest = {(b.wine.lwin, b.wine.vintage, (b.currency or settings.current.currency).upper()) for b in bottles if b not in from_bi}
        items = [_item(label(b), (f"{money(b.last_price, b)} on {b.last_price_date:%d %b %Y}" if b.last_price
                                  and b.last_price_date else "no price yet")
                       + (" · Bordeaux Index" if b in from_bi else ""), link(b)) for b in bottles]
        return {"summary": f"{_n(len(bottles), 'cellar bottle')} with an LWIN{scope}: "
                           f"{len(from_bi)} from your Bordeaux Index portfolio; for the rest ({_n(len(rest), 'wine')}) "
                           f"a run asks the BI market{' then WineLabs.ai' if prices.api_key() else ''} "
                           f"(~{max(1, len(rest) // 30)} min).", "items": items[:MAX_ITEMS]}
    if not prices.pricing_available():
        raise RuntimeError("No price source: set WINELABS_API_KEY (or the BI_ login) in .secrets.env")
    done = prices.refresh_prices(session, bottles, log=job.log)
    items = [_item(label(b), f"{money(old, b) if old else '–'} → {money(new, b) if new else 'no price'}",
                   link(b)) for b, old, new in done if new is None or old is None or abs(new - old) >= 0.5]
    found = sum(1 for _, _, p in done if p)
    return {"summary": f"{found} of {_n(len(done), 'bottle')} priced; {len(items)} changed or without a price.",
            "items": items[:MAX_ITEMS]}


def _prices_force(session, job):
    return _prices(session, job, force=True)


def _map_pack(session, job):
    """The map data pack (map_pack.py): the preview says what the store has and where the pack is; a run downloads
    it, puts its outlines in the store, then links the appellations and vineyards to them (shape links)."""
    import geo
    import map_pack
    import shape_links
    have = map_pack.installed()
    items = [_item(name, f"{m.get('rows', '?')} outlines" + (f" · {m['licence']}" if m.get("licence") else ""))
             for name, m in sorted(have.items())]
    where = map_pack.MAP_PACK_URL or "no address (MAP_PACK_URL)"
    if not job.commit:
        return {"summary": (f"The store has {_n(len(have), 'source')}" if have else "No map outlines yet")
                           + f"; a run downloads the pack from {where} and links the outlines.", "items": items}
    path, temporary = map_pack.fetch(map_pack.MAP_PACK_URL, log=job.log)
    try:
        done = map_pack.install(path, log=job.log)
    finally:
        if temporary:
            os.remove(path)
    result = shape_links.link(session.get_bind(), geo.GEO_DIR, commit=True)
    linked = sum(sum(t["linked"].values()) for t in result["tables"].values())
    return {"summary": f"{_n(len(done), 'source')} installed ({sum(done.values())} outlines); {linked} appellations "
                       f"and vineyards linked to their outline.", "items": []}


def _shape_links(session, job):
    import geo
    import shape_links
    try:
        result = shape_links.link(session.get_bind(), geo.GEO_DIR, commit=job.commit)
    except ValueError as e:
        raise RuntimeError(str(e))
    items, counts = [], []
    for table, t in result["tables"].items():
        kind = "vineyard" if table == "vineyards" else "appellation"
        page = "/vineyards" if table == "vineyards" else "/appellations"
        for row, old, new in t["changes"]:
            detail = f"{old or 'no outline'} → {new or 'no outline'}"
            items.append(_item(row["name"], detail, f"{page}/{row['id']}"))
            job.log(f"{row['name']}: {detail}")
        for row, tried in t["missing"]:
            items.append(_item(row["name"], f"no shape in the store for {' / '.join(tried)}", f"{page}/{row['id']}"))
        for row, options in t["ambiguous"]:
            items.append(_item(row["name"], f"ambiguous, not linked: {' or '.join(options)}", f"{page}/{row['id']}"))
        linked = sum(t["linked"].values())
        counts.append(f"{linked} of {_n(t['rows'], kind)} linked")
    changes = sum(len(t["changes"]) for t in result["tables"].values())
    verb = "saved" if job.commit else "to save"
    return {"summary": f"{'; '.join(counts)}. {_n(changes, 'change')} {verb}"
                       + (f" (store not built for: {', '.join(result['absent'])})" if result["absent"] else "") + ".",
            "items": items[:MAX_ITEMS]}


def _lieux_dits(session, job):
    """The cuvées whose name holds a lieu-dit eligible for their appellation (lieux_dits.py): a preview to tick (a
    single possible lieu-dit ticked, several to choose from), then the ticked ones linked (params "keys":
    "<wine id>=<lieu-dit id>")."""
    import lieux_dits as ld
    found = ld.candidates(session)
    if found is None:
        raise RuntimeError("No lieux-dits in the map store yet: Map outlines downloads them (or "
                           "geo_scripts/etl_lieux_dits.py builds them)")
    items = []
    for wines, options in found:
        w = wines[0]
        wine = f"{w.producer.name} {w.cuvee} ({w.appellation.name}), {_n(len(wines), 'vintage')}"
        for sid, name, d in options:
            share = f" · {round(d['vines'] * 100)}% in vines" if d.get("vines") is not None else ""
            items.append(_item(f"{name} · {d.get('commune_name') or '?'}", f"{wine}{share}", f"/wines/{w.id}",
                               pick={"key": f"{w.id}={sid}", "group": w.producer.name, "on": ld.sure(options),
                                     "map": f"/api/wines/{w.id}/shapes?lieu_dit={sid}"}))
    if not job.commit:
        sure = sum(1 for _, options in found if ld.sure(options))
        return {"summary": f"{_n(len(found), 'cuvée')} name a lieu-dit of their appellation: {sure} sure (ticked), "
                           f"{len(found) - sure} to check (a name found in several villages, or a lieu-dit mostly "
                           f"not in vines).",
                "items": items[:MAX_ITEMS]}
    keys, linked, cuvees = set(job.params.get("keys") or []), 0, 0
    for wines, options in found:
        for sid, name, d in options:
            if f"{wines[0].id}={sid}" in keys:
                v = ld.link(session, wines, sid, name, d)
                job.log(f"{wines[0].producer.name} {wines[0].cuvee}: {v.name} ({v.village})")
                linked, cuvees = linked + len(wines), cuvees + 1
                break
    session.commit()
    return {"summary": f"{_n(cuvees, 'cuvée')} linked to their lieu-dit ({_n(linked, 'wine')}, every vintage).",
            "items": [it for it in items if it["pick"]["key"] in keys][:MAX_ITEMS]}


def _keys_params(body, commit):
    if commit and not body.keys:
        raise HTTPException(422, "Tick at least one suggestion")
    return {"keys": body.keys if commit else []}


def _backup(session, job):
    """Every main table to CSV; with SQLite, a copy of the database too (SQLite's own backup: consistent while the
    app runs). A Postgres database is dumped with Postgres's own tools (pg_dump), into the backups folder."""
    from tasks.backup import backup_csv
    engine = session.get_bind()
    folder = backup_csv(engine, BACKUP_DIR, log=job.log)
    saved = [f"backups/{os.path.basename(folder)}"]
    if engine.dialect.name == "sqlite":
        import sqlite3
        from datetime import datetime
        target = os.path.join(BACKUP_DIR, f"winelib_{datetime.now():%Y-%m-%d_%H%M}.sqlite")
        source = sqlite3.connect(engine.url.database)
        try:
            with sqlite3.connect(target) as copy:
                source.backup(copy)
        finally:
            source.close()
        job.log(f"Database copied to {target}")
        saved.append(f"backups/{os.path.basename(target)}")
    return {"summary": f"Saved in {' and '.join(saved)}.", "items": []}


def _pairs(body, commit):
    if not body.pairs:
        raise HTTPException(422, "Pick at least one pair to merge")
    return {"pairs": [p.model_dump() for p in body.pairs]}


def _cellar_csv_params(body, commit):
    if not (body.text or "").strip():
        raise HTTPException(422, "Choose a CSV file")
    if commit and not body.keys:
        raise HTTPException(422, "Preview first, then tick the rows to import")
    return {"_text": body.text, "mapping": body.mapping, "keys": body.keys if commit else []}


def _scores_csv_params(body, commit):
    if not (body.text or "").strip():
        raise HTTPException(422, "Choose a CSV file")
    if not " ".join((body.critic or "").split()):
        raise HTTPException(422, "Which critic are these reviews by?")
    if commit and not body.keys:
        raise HTTPException(422, "Preview first, then tick the rows to import")
    return {"_text": body.text, "critic": body.critic, "mapping": body.mapping, "keys": body.keys if commit else []}


# How the Settings page groups the tasks, in this order
GROUPS = ["Clean up", "LWIN and prices", "Import", "Maps and places", "Backup"]  # plug-ins add theirs

def _no_lwin_list():
    from tasks import match_lwin
    return None if os.path.exists(match_lwin.LWIN_DB) else "Needs the LWIN list (see Integrations)."


def _no_price_source():
    from tasks import bordeaux_index
    from tasks import update_market_prices as prices
    if bordeaux_index.configured() or prices.api_key():
        return None
    return "Needs Bordeaux Index or WineLabs.ai (see Integrations)."


def _no_map_pack():
    import map_pack
    return None if map_pack.MAP_PACK_URL else "No download address set (MAP_PACK_URL)."


TASKS = {
    "duplicates": {"group": "Clean up", "title": "Duplicate wines", "fn": _duplicates, "preview": True, "writes": True,
                   "description": "Same producer, cuvée, color, appellation, grape and vintage: move the cellar lines to one wine and delete the others."},
    "appellations_apart": {"group": "Clean up", "title": "Cuvées under several appellations", "fn": _appellations_apart,
                           "preview": False, "writes": False,
                           "description": "A cuvée filed under more than one appellation: a vintage entered twice, "
                                          "or one left under an old name."},
    "orphans": {"group": "Clean up", "title": "Orphans", "fn": _orphans, "preview": False, "writes": False,
                "description": "Tasting notes without a bottle, bottles without a wine."},
    "similar": {"group": "Clean up", "title": "Similar cuvée names", "fn": _similar, "preview": False, "writes": False,
                "description": "Cuvées of one producer that are probably the same one spelled two ways."},
    "similar_producers": {"group": "Clean up", "title": "Duplicate producers", "fn": _similar_producers, "preview": False,
                          "writes": False,
                          "description": "Producers probably entered twice (same name but for accents and case, or "
                                         "the same words without Domaine, Bodegas, Weingut...): pick one to keep."},
    "cellar_csv": {"group": "Import", "title": "Import a cellar", "fn": _cellar_csv, "preview": True,
                   "writes": True, "upload": True, "params": _cellar_csv_params,
                   "description": "A CSV of wines, bottles and tastings: another app's export (CellarTracker, Vivino) "
                                  "or your spreadsheet, columns recognised by their header. Producers, wines and "
                                  "grapes you don't have are created; nothing already there is added twice."},
    "scores_csv": {"group": "Import", "title": "Import critic scores", "fn": _scores_csv, "preview": True,
                   "writes": True, "upload": True, "critic": True, "params": _scores_csv_params,
                   "description": "A CSV of one critic's reviews (an export, your notes): producer, cuvée, vintage, "
                                  "colour, grape, appellation, score, note, link, date, recognised by their header. "
                                  "Scores go to the wines you have; the others are added as new wines."},
    "places": {"group": "Maps and places", "title": "Place coordinates", "fn": _places, "preview": True, "writes": True, "limit": 10, "unit": "places",
               "description": "Find places without coordinates on OpenStreetMap (one per second)."},
    "lwin": {"group": "LWIN and prices", "title": "LWIN codes", "fn": _lwin, "preview": True, "writes": True, "unavailable": _no_lwin_list,
             "description": "Match cellar wines without an LWIN to the Liv-ex list (needed for market prices). A run "
                            "saves only sure matches; the others are listed to pick in the wine form."},
    "prices": {"group": "LWIN and prices", "title": "Market prices", "fn": _prices, "preview": True, "writes": True, "unavailable": _no_price_source,
               "description": "Refresh the market price of every cellar bottle with an LWIN, except those already "
                              f"priced in the last {PRICE_MAX_AGE_DAYS} days: Bordeaux Index (your portfolio, "
                              "else its LiveTrade market), WineLabs.ai for wines BI doesn't quote."},
    "prices_force": {"group": "LWIN and prices", "title": "Market prices · force refresh", "fn": _prices_force, "preview": True, "writes": True,
                     "unavailable": _no_price_source,
                     "description": "Like Market prices, but every cellar bottle with an LWIN, whatever its price's "
                                    "age."},
    "map_pack": {"group": "Maps and places", "title": "Map outlines", "fn": _map_pack, "preview": True, "writes": True, "unavailable": _no_map_pack,
                 "description": "Download the map's outlines (appellations of France, the EU, the US and Australia, "
                                "Burgundy's premiers crus) into the shape store, then link them. Their credits are "
                                "listed in Settings."},
    "lieux_dits": {"group": "Maps and places", "title": "Lieux-dits for your wines", "fn": _lieux_dits, "preview": True,
                   "writes": True, "params": _keys_params,
                   "description": "French cuvées named after a lieu-dit of their appellation (Le Bourg, Les Poyeux): "
                                  "linked to it as their vineyard, its outline from the cadastre. A preview to tick "
                                  "first; a name found in several villages is yours to choose."},
    "shape_links": {"group": "Maps and places", "title": "Shape links", "fn": _shape_links, "preview": True, "writes": True,
                    "description": "Link appellations and vineyards to their outline in the shape store (after "
                                   "adding some, or a rebuilt store): what changes, and what has no outline."},
    "backup": {"group": "Backup", "title": "Backup", "fn": _backup, "preview": False, "writes": False,
               "description": "Every main table to CSV, in a new folder of backups/; with a SQLite database, a copy "
                              "of it too (a Postgres database isn't copied: dump it with pg_dump)."},
    # Started from the similar cuvée names report, not listed
    "merge_cuvees": {"group": "Clean up", "title": "Merge cuvée names", "fn": _merge_cuvees, "preview": True, "writes": True, "params": _pairs,
                     "hidden": True, "description": "Merge picked pairs of cuvée names."},
    # Started from the duplicate producers report, not listed
    "merge_producers": {"group": "Clean up", "title": "Merge producers", "fn": _merge_producers, "preview": True, "writes": True, "params": _pairs,
                        "hidden": True, "description": "Merge picked pairs of producers."},
}


@router.get("/api/maintenance")
def maintenance():
    """The tasks with their last run, and the current (or last) job."""
    last = jobs.history()
    job = jobs.current()
    return {
        "tasks": [{"id": k, "group": t["group"], "title": t["title"], "description": t["description"],
                   "preview": t["preview"], "writes": t["writes"], "limit": t.get("limit"), "unit": t.get("unit"),
                   "upload": t.get("upload", False), "critic": t.get("critic", False),
                   # what it needs first (an integration, an address), shown instead of its buttons
                   "unavailable": t["unavailable"]() if t.get("unavailable") else None,
                   "last": last.get(k)}
                  for k, t in TASKS.items() if not t.get("hidden")],
        "groups": GROUPS,
        # every task's group, the hidden ones too: the job's panel opens under it
        "task_groups": {k: t["group"] for k, t in TASKS.items()},
        "job": job.public() if job else None,
    }


class MergePair(BaseModel):
    """merge_cuvees: a producer and two cuvée names; merge_producers: two producer ids."""
    producer_id: int | None = None
    keep: str | int
    drop: str | int


class RunBody(BaseModel):
    commit: bool = False
    limit: int | None = None
    pairs: list[MergePair] = []
    keys: list[str] = []  # the suggestions ticked in a preview (scores_csv: line numbers)
    # suggestion -> the wine as edited in the preview (PickCard): {"cuvee", "vintage", "type", "appellation",
    # "varietal" (an id, or {"name"} to create), "wine" (a model's id, optional)}
    targets: dict[str, dict] = {}  # suggestions as edited in the preview (a plug-in's: robert_parker reads them)
    # The imports: the file's text, the critic (scores), and {field: header} when the columns were picked by hand
    text: str | None = Field(None, max_length=20_000_000)
    critic: str | None = None
    mapping: dict[str, str] | None = None


@router.post("/api/maintenance/{task}", status_code=202)
def run(task: str, body: RunBody, session: Session = Depends(get_session)):
    """Starts a task: a preview (commit false; only for tasks with one) or a run."""
    t = TASKS.get(task)
    if t is None:
        raise HTTPException(404, "No such task")
    commit = body.commit or not t["preview"]
    params = {"limit": max(1, min(body.limit or t.get("limit") or 0, 200))} if t.get("limit") else {}
    if t.get("params"):  # the task's own: picks, ticks, an uploaded file...
        params = t["params"](body, commit)
    # The job's sessions use the same database as this request (tests point it elsewhere)
    make_session = sessionmaker(bind=session.get_bind())
    job = jobs.start(task, t["title"], t["fn"], make_session, commit, params)
    if job is None:
        raise HTTPException(409, "Another maintenance job is running")
    return job.public()


@router.get("/api/maintenance/wine")
def wine_lookup(producer_id: int, cuvee: str = "", vintage: str = "", type: str = "", appellation: int | None = None,
                appellation_name: str = "", varietal: int | None = None, varietal_name: str = "", critic: str = "",
                session: Session = Depends(get_session)):
    """For a suggestion edited in an import's preview (PickCard): the wine it would go to, if you have it (with that
    critic's score), or null: the import would create it. An appellation / grape typed by name counts if it exists."""
    from sqlalchemy import func
    from db import Appellation, Varietal
    from tasks.matching import find_wine
    from models import has_score

    def by_name(model, value, name):
        if value is not None or not name.strip():
            return value
        row = session.query(model.id).filter(func.lower(model.name) == name.strip().lower()).first()
        return row[0] if row else -1  # a name that doesn't exist yet: no wine can have it
    fields = {"cuvee": cuvee, "vintage": vintage.strip() or None, "type": type or None,
              "appellation_id": by_name(Appellation, appellation, appellation_name),
              "varietal_id": by_name(Varietal, varietal, varietal_name)}
    w = find_wine(session, producer_id, fields)
    if w is None:
        return None
    s = w.score_of(critic)
    return {"id": w.id, "score": s.score if has_score(s) else None, "url": (s.url or None) if s else None}


@router.get("/api/maintenance/job")
def job_status():
    job = jobs.current()
    return job.public() if job else None


@router.post("/api/maintenance/job/stop")
def stop():
    job = jobs.current()
    if job and job.status == "running":
        job.stop.set()
    return {"ok": True}


# --- Backups --------------------------------------------------------------------------------------------

def _backups():
    if not os.path.isdir(BACKUP_DIR):
        return []
    out = []
    for name in os.listdir(BACKUP_DIR):
        path = os.path.join(BACKUP_DIR, name)
        if os.path.isdir(path) and any(f.endswith(".csv") for f in os.listdir(path)):
            size = sum(os.path.getsize(os.path.join(path, f)) for f in os.listdir(path))
            out.append({"name": name, "kind": "csv", "size": size, "modified": os.path.getmtime(path)})
        elif name.endswith((".sql", ".sqlite")) and os.path.isfile(path):
            out.append({"name": name, "kind": name.rsplit(".", 1)[1], "size": os.path.getsize(path),
                        "modified": os.path.getmtime(path)})
    return sorted(out, key=lambda b: -b["modified"])


@router.get("/api/maintenance/backups")
def backups():
    """Database dumps (.sql, a Postgres dump put in the backups folder; .sqlite, the backup task's copy of a SQLite
    database) and CSV backups,
    newest first."""
    return _backups()[:50]


@router.get("/api/maintenance/backups/{name}")
def download_backup(name: str):
    """A database dump or copy as is; a CSV backup folder as a zip."""
    entry = next((b for b in _backups() if b["name"] == name), None)  # only names we listed: no path tricks
    if entry is None:
        raise HTTPException(404, "No such backup")
    path = os.path.join(BACKUP_DIR, name)
    if entry["kind"] in ("sql", "sqlite"):
        return FileResponse(path, media_type="application/sql" if entry["kind"] == "sql" else "application/vnd.sqlite3",
                            filename=name)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(os.listdir(path)):
            z.write(os.path.join(path, f), arcname=f"{name}/{f}")
    return Response(buf.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="winelib_{name}.zip"'})


# For plug-ins (plugins.py): a report line, "3 wines"
item = _item
plural = _n
