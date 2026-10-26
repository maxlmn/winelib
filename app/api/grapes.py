"""Grape profiles (climate, colour depth, acidity, tannin, aromas, notes, classic regions), from the varietal's
columns (reference data: varietals.csv)."""

FIELDS = [  # (column, label)
    ("climate", "Climate"), ("depth", "Colour depth"), ("acidity", "Acidity"), ("acid_shape", "Acid shape"),
    ("acid_type", "Acid type"), ("tannin", "Tannin"), ("tannin_type", "Tannin type"),
    ("tannin_location", "Tannin felt on"), ("aromas", "Primary aromas"),
]
COLUMNS = [c for c, _ in FIELDS] + ["notes", "classic_regions"]


def regions_of(text):
    """"Germany: Mosel, Rheingau | France : Alsace" -> one entry per country"""
    return [r.strip() for r in (text or "").split("|") if r.strip()]


def has_profile(v):
    return any((getattr(v, c) or "").strip() for c in COLUMNS)


def profile(v):
    """{"facts": [{label, value}], "notes", "regions": [...]}, or None when the grape has none."""
    if not has_profile(v):
        return None
    return {
        "facts": [{"label": label, "value": getattr(v, col).strip()} for col, label in FIELDS
                  if (getattr(v, col) or "").strip()],
        "notes": (v.notes or "").strip() or None,
        "regions": regions_of(v.classic_regions),
    }
