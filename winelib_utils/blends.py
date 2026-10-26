"""A wine's blend: its style (one of BLEND_STYLES, or none) and the grapes it's made of (wine_grapes, the first the
main one; docs/history/blends.md). Shared by the app and the imports."""
import re
import unicodedata

# Field blend: co-planted, co-fermented grapes (Wiener Gemischter Satz, António Madeira's old Dão vines)
BLEND_STYLES = ["Bordeaux blend", "Rhône blend", "Champagne blend", "Field blend", "Other blend"]

# What older free texts and imports call a style
_STYLES = {
    "bordeaux": "Bordeaux blend", "bordeau": "Bordeaux blend", "meritage": "Bordeaux blend",
    "rhone": "Rhône blend", "southern": "Rhône blend", "gsm": "Rhône blend",
    "champagne": "Champagne blend",
    "field": "Field blend", "gemischter": "Field blend",
}


def _key(text):
    t = "".join(c for c in unicodedata.normalize("NFKD", str(text or "")).casefold() if not unicodedata.combining(c))
    return " ".join(re.findall(r"\w+", t))


def blend_style(text):
    """A style from a text: one of BLEND_STYLES as it is, a known name ("Bordeaux Blend", "Rhone Blend", "GSM"), any
    other blend "Other blend"; None for none."""
    key = _key(text)
    if not key:
        return None
    for style in BLEND_STYLES:
        if key == _key(style):
            return style
    # its first word that names one ("Red Bordeaux Blend", CellarTracker's): Bordeaux
    return next((_STYLES[w] for w in key.split() if w in _STYLES), "Other blend")


def names_a_style(text):
    """Whether a grape column's text is a blend style rather than grapes: "Red Bordeaux Blend", "GSM", "Meritage"."""
    words = _key(text).split()
    return "blend" in words or words in (["gsm"], ["meritage"])
