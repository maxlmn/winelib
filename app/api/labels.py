"""Which uploaded label a wine shows: its own, else the nearest vintage's of the same cuvée (a label rarely changes but
for its year). For lists of wines (a producer's page, the cellar); a wine's own page asks for its one (details._label)."""
import photos
from display import vintage_label


def _year(vintage):
    try:
        return int(str(vintage)[:4])
    except (TypeError, ValueError):
        return None


def by_wine(wines, index=None):
    """{wine id: {url, from_vintage}} of the wines with a label, their own else the nearest vintage's of the same
    cuvée (same producer, cuvée, appellation and grape). `wines`: rows or objects with id, producer_id, cuvee,
    appellation_id, varietal_id, vintage, disgorgement_date; the vintages that have the label among them."""
    labels = photos.label_index() if index is None else index
    if not labels:
        return {}
    families = {}
    for w in wines:
        families.setdefault((w.producer_id, w.cuvee or "", w.appellation_id, w.varietal_id), []).append(w)
    out = {}
    for family in families.values():
        with_label = [x for x in family if x.id in labels]
        if not with_label:
            continue
        for w in family:
            year = _year(w.vintage)

            def gap(x):
                y = _year(x.vintage)
                return (x.id != w.id, abs(y - year) if y is not None and year is not None else 9999)
            source = min(with_label, key=gap)
            out[w.id] = {"url": photos.url_for(labels[source.id]),
                         "from_vintage": None if source.id == w.id else vintage_label(source.vintage, source.disgorgement_date)}
    return out


def of_cellar(session, wine_ids):
    """by_wine for these wines (a cellar's lines), their cuvées' other vintages with a label read along"""
    from db import Wine
    index = photos.label_index()
    ids = set(wine_ids)
    if not index or not ids:
        return {}
    cols = (Wine.id, Wine.producer_id, Wine.cuvee, Wine.appellation_id, Wine.varietal_id, Wine.vintage, Wine.disgorgement_date)
    rows = session.query(*cols).filter(Wine.id.in_(ids | set(index))).all()
    found = by_wine(rows, index)
    return {i: found[i] for i in ids if i in found}
