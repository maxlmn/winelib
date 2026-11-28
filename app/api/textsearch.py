"""Accent- and case-insensitive matching for type-aheads and global search: "cote rotie" finds "Côte-Rôtie",
"evangile" finds "L'Évangile". Done in Python so it behaves the same on SQLite and Postgres."""
import re
import unicodedata
from functools import lru_cache


@lru_cache(maxsize=65536)
def fold(s):
    """Lowercase without accents; hyphens and apostrophes become spaces."""
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return s.replace("-", " ").replace("'", " ").replace("’", " ")


def words(s):
    """fold(), then only its letters and digits, one space apart: "Muscat À Petits-Grains" -> "muscat a petits grains"
    (names matched whatever their punctuation)"""
    return " ".join(re.findall(r"[a-z0-9]+", fold(s)))


def one_off(a, b):
    """a and b differ by one letter at most: one left out, one too many, or one changed ("fournaux", "fourneaux")"""
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) > len(b):
        a, b = b, a
    i = 0
    while i < len(a) and a[i] == b[i]:
        i += 1
    return a[i + 1:] == b[i + 1:] if len(a) == len(b) else a[i:] == b[i + 1:]


def near(w, h):
    """A word of 5 letters or more one letter off a word of h (a misspelling, or a name spelt two ways)"""
    return len(w) >= 5 and any(one_off(w, x) for x in re.findall(r"[a-z0-9]+", h))


def matches(q, *fields, typos=False):
    """Rank of a match (lower is better) or None: every word must appear in one of the fields.
    Rank 0 when the first field starts with the whole query, 1 when it starts with one of its words, 2 elsewhere;
    with typos, a word one letter off a field's word (5 letters or more) matches too, ranked 3."""
    words = fold(q).split()
    hay = [fold(f) for f in fields]
    if not all(any(w in h for h in hay) for w in words):
        if typos and all(any(w in h or near(w, h) for h in hay) for w in words):
            return 3
        return None
    head = hay[0]
    return 0 if head.startswith(fold(q).strip()) else 1 if any(head.startswith(w) for w in words) else 2


def search(rows, q, fields, limit):
    """The best `limit` rows for query q; `fields(row)` gives the texts to match, the first one ranks. Short of
    `limit`, the rows one letter off follow ("fournaux" finds "Aux Fourneaux")."""
    if not q or not q.strip():
        return rows[:limit]
    ranked = [(r, i, row) for i, row in enumerate(rows) if (r := matches(q, *fields(row))) is not None]
    if len(ranked) < limit and any(len(w) >= 5 for w in fold(q).split()):
        found = {i for _, i, _ in ranked}
        ranked += [(r, i, row) for i, row in enumerate(rows)
                   if i not in found and (r := matches(q, *fields(row), typos=True)) is not None]
    return [row for _, _, row in sorted(ranked, key=lambda x: (x[0], x[1]))][:limit]
