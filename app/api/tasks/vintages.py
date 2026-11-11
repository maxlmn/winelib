"""A cuvée's vintages, checked against each other (Settings › Maintenance): one cuvée (producer, name, colour) filed
under several appellations, often the same wine entered twice or a vintage left under an old name (Vin de France one
year, Hautes-Côtes the next). (A vintage's vineyard needs no check: a new one takes its other vintages', and one set
on a vintage goes to the others: routers/forms.py.)
"""
from collections import defaultdict

from sqlalchemy.orm import joinedload, lazyload

from models import Wine


def _cuvee(w):
    return (w.cuvee or "").strip().lower()


def appellations_apart(session):
    """[{"wine": a wine of the cuvée, "by": [(appellation name, [vintages])], "both": [vintages under two]}]: the
    cuvées filed under more than one appellation; `both` the vintages found under several (likely entered twice)."""
    groups = defaultdict(list)
    # Plain columns first, to find the cuvées under more than one appellation; only their wines are loaded whole
    # (the home page asks at each visit, and loading every wine was most of its wait on a large cellar)
    under = defaultdict(lambda: (set(), []))
    for i, producer_id, cuvee, colour, appellation_id in session.query(
            Wine.id, Wine.producer_id, Wine.cuvee, Wine.type, Wine.appellation_id):
        if producer_id and (cuvee or "").strip():
            appellations, ids = under[(producer_id, cuvee.strip().lower(), colour)]
            appellations.add(appellation_id)
            ids.append(i)
    apart = [i for appellations, ids in under.values() if len(appellations) > 1 for i in ids]
    if not apart:
        return []
    # its critics' scores loaded only if asked
    for w in session.query(Wine).filter(Wine.id.in_(apart)).options(
            joinedload(Wine.producer), joinedload(Wine.appellation), lazyload(Wine.scores)):
        if w.producer_id and _cuvee(w):  # a wine without a cuvée name is its appellation's: two are two wines
            groups[(w.producer_id, _cuvee(w), w.type)].append(w)
    out = []
    for ws in groups.values():
        by = defaultdict(list)
        for w in ws:
            by[w.appellation.name if w.appellation else "No appellation"].append(str(w.vintage or "NV"))
        if len(by) < 2:
            continue
        seen = defaultdict(int)
        for vintages in by.values():
            for v in set(vintages):
                seen[v] += 1
        out.append({"wine": max(ws, key=lambda w: str(w.vintage or "")),
                    "by": sorted(((a, sorted(v)) for a, v in by.items()), key=lambda x: x[0]),
                    "both": sorted(v for v, n in seen.items() if n > 1)})
    return sorted(out, key=lambda x: (not x["both"], x["wine"].producer.name, _cuvee(x["wine"])))
