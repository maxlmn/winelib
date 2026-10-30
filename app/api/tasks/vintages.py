"""A cuvée's vintages, checked against each other (Settings › Maintenance):

- vineyard gaps: vintages without a vineyard whose other vintages (same producer, cuvée, appellation and grape, as
  the wine page lists them) all have the same one: given it, as a new vintage is;
- appellations apart: one cuvée (producer, name, colour) filed under several appellations, often the same wine
  entered twice or a vintage left under an old name (Vin de France one year, Hautes-Côtes the next).
"""
from collections import defaultdict

from sqlalchemy.orm import joinedload

from models import Wine


def _cuvee(w):
    return (w.cuvee or "").strip().lower()


def vineyard_gaps(session):
    """[(vineyard, [wines without it])]: the cuvées some of whose vintages lack the vineyard all the others share."""
    groups = defaultdict(list)
    for w in session.query(Wine).options(joinedload(Wine.producer), joinedload(Wine.vineyard)):
        groups[(w.producer_id, _cuvee(w), w.appellation_id, w.varietal_id)].append(w)
    out = []
    for ws in groups.values():
        found = {w.vineyard_id for w in ws if w.vineyard_id}
        missing = [w for w in ws if not w.vineyard_id]
        if len(found) == 1 and missing:
            vineyard = next(w.vineyard for w in ws if w.vineyard_id)
            out.append((vineyard, sorted(missing, key=lambda w: str(w.vintage or ""))))
    return sorted(out, key=lambda x: (x[1][0].producer.name if x[1][0].producer else "", _cuvee(x[1][0])))


def fill_vineyard_gaps(session, gaps):
    """Gives each gap's wines their vineyard; the wines given it."""
    n = 0
    for vineyard, wines in gaps:
        for w in wines:
            w.vineyard_id = vineyard.id
            n += 1
    session.commit()
    return n


def appellations_apart(session):
    """[{"wine": a wine of the cuvée, "by": [(appellation name, [vintages])], "both": [vintages under two]}]: the
    cuvées filed under more than one appellation; `both` the vintages found under several (likely entered twice)."""
    groups = defaultdict(list)
    for w in session.query(Wine).options(joinedload(Wine.producer), joinedload(Wine.appellation)):
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
