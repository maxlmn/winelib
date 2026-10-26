import sys
import os
import re
from collections import defaultdict
from unidecode import unidecode
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, joinedload

# Add project root to path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import paths
from models import Wine, Producer

def normalize_cuvee(name):
    """
    Lowercase, remove accents, remove non-alphanumeric characters.
    """
    if not name:
        return ""
    # Simplify
    n = unidecode(name).lower()
    # Remove special chars (keep only letters and numbers)
    n = re.sub(r'[^a-z0-9]', '', n)
    return n

def find_similar(session):
    """Cuvée names of the same producer that are probably one cuvée spelled two ways:
    [{"producer_id", "producer", "reason", "a": (cuvée, [wine ids]), "b": (cuvée, [wine ids])}]."""
    wines = session.query(Wine).options(joinedload(Wine.producer)).filter(Wine.cuvee != None).all()  # noqa: E711
    wines_by_producer = defaultdict(list)
    for w in wines:
        if w.producer_id:
            wines_by_producer[w.producer_id].append(w)
    pairs = []
    for pid, p_wines in wines_by_producer.items():
        cuvee_map = defaultdict(list)
        colors = defaultdict(set)
        for w in p_wines:
            if w.cuvee:
                cuvee_map[w.cuvee].append(w.id)
                colors[w.cuvee].add(w.type)
        names = list(cuvee_map)
        reported = set()
        for i, c1 in enumerate(names):
            n1 = normalize_cuvee(c1)
            if not n1:
                continue
            for c2 in names[i + 1:]:
                n2 = normalize_cuvee(c2)
                # Only names sharing a color can be one cuvée (a red and a white aren't)
                if not n2 or c1 == c2 or not colors[c1] & colors[c2]:
                    continue
                if n1 == n2:
                    reason = "Identical normalized"
                elif len(n1) > 3 and n1 in n2:
                    reason = f"'{c1}' inside '{c2}'"
                elif len(n2) > 3 and n2 in n1:
                    reason = f"'{c2}' inside '{c1}'"
                else:
                    continue
                if frozenset([c1, c2]) not in reported:
                    reported.add(frozenset([c1, c2]))
                    pairs.append({"producer_id": pid, "producer": p_wines[0].producer.name, "reason": reason,
                                  "a": (c1, cuvee_map[c1]), "b": (c2, cuvee_map[c2])})
    return sorted(pairs, key=lambda p: p["producer"].lower())


def find_similar_cuvees():
    print("🚀 Connecting to database...")
    session = sessionmaker(bind=create_engine(paths.DB_URL))()
    try:
        pairs = find_similar(session)
        for p in pairs:
            print(f"[Producer: {p['producer']}]")
            print(f"  Similarity: {p['reason']}")
            print(f"    1. '{p['a'][0]}' (IDs: {p['a'][1]})")
            print(f"    2. '{p['b'][0]}' (IDs: {p['b'][1]})")
            print("-" * 40)
        print(f"\nDone. Found {len(pairs)} similar pairs.")
    finally:
        session.close()


if __name__ == "__main__":
    find_similar_cuvees()
