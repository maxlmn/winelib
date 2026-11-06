"""What a grape's page says of it, beyond the reference data: Pl@ntGrape's variety sheets (origin, description, ripening,
its growing and wines) and the University of Adelaide's planted areas (hectares by country and region).

From data/grapes/grapes.json, shipped with the app; nothing is looked up while you use it. That file has its own
licence, CC BY-NC-SA 4.0 (data/grapes/LICENSE), not the code's MIT: without it, grapes' pages just don't show this.
"""
import json
import os
import re
import threading
import unicodedata

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "grapes", "grapes.json")

# A family, not a grape: its VIVC number in the reference data is one of its members' (Muscat Ottonel), not said of them all
FAMILIES = {"muscat"}

_lock = threading.Lock()
_loaded = None  # ({vivc: grape}, {folded name: grape}, the file's sources)


def _fold(name):
    plain = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower()
    return " ".join(re.findall(r"[a-z0-9]+", plain))


def reset():
    """Forget what was read (tests point PATH elsewhere)."""
    global _loaded
    with _lock:
        _loaded = None


def _data():
    global _loaded
    with _lock:
        if _loaded is None:
            try:
                with open(PATH, encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, ValueError):
                data = {"grapes": [], "sources": []}
            grapes = data["grapes"]
            _loaded = ({g["vivc"]: g for g in grapes if g.get("vivc")},
                       {_fold(n): g for g in grapes for n in g.get("names", [])}, data["sources"])
        return _loaded


def about(grape):
    """What's known of a grape, found by its VIVC number, else its name: {"found": True, "name", "sheet", "planted",
    "credits"} (the credits of the sources it has), or {"found": False}."""
    if _fold(grape.name) in FAMILIES:
        return {"found": False}
    by_vivc, by_name, sources = _data()
    found = by_vivc.get(grape.vivc) or by_name.get(_fold(grape.name))
    if not found:
        return {"found": False}
    return {"found": True, "name": found.get("name") or grape.name, "sheet": found.get("sheet"),
            "planted": found.get("planted"), "credits": [s for s in sources if found.get(s["key"])]}
