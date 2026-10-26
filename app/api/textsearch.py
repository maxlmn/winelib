"""Accent- and case-insensitive matching for type-aheads and global search: "cote rotie" finds "Côte-Rôtie",
"evangile" finds "L'Évangile". Done in Python so it behaves the same on SQLite and Postgres."""
import unicodedata
from functools import lru_cache


@lru_cache(maxsize=65536)
def fold(s):
    """Lowercase without accents; hyphens and apostrophes become spaces."""
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return s.replace("-", " ").replace("'", " ").replace("’", " ")


def matches(q, *fields):
    """Rank of a match (lower is better) or None: every word must appear in one of the fields.
    Rank 0 when the first field starts with the whole query, 1 when it starts with one of its words."""
    words = fold(q).split()
    hay = [fold(f) for f in fields]
    if not all(any(w in h for h in hay) for w in words):
        return None
    head = hay[0]
    return 0 if head.startswith(fold(q).strip()) else 1 if any(head.startswith(w) for w in words) else 2


def search(rows, q, fields, limit):
    """The best `limit` rows for query q; `fields(row)` gives the texts to match, the first one ranks."""
    if not q or not q.strip():
        return rows[:limit]
    ranked = [(r, i, row) for i, row in enumerate(rows) if (r := matches(q, *fields(row))) is not None]
    return [row for _, _, row in sorted(ranked, key=lambda x: (x[0], x[1]))][:limit]
