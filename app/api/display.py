"""How dates, vintages and vineyards are written in the API's answers, the same on every page."""
from datetime import date


def iso(d):
    """A date as "2024-03-09" (a text as it is, None as None)."""
    if d is None:
        return None
    return d.isoformat() if isinstance(d, date) else str(d)


def vintage_label(vintage, disgorged=None):
    """"2016"; "NV", or "NV - 2019" with its disgorgement date."""
    vintage = vintage or "NV"
    return f"NV - {disgorged}" if vintage == "NV" and disgorged else vintage


def vineyard_label(v):
    """"Côte de Beaune - Meursault - Les Perrières": the vineyard's place and name."""
    return " - ".join(p for p in (v.sub_region, v.village, v.name) if p and str(p).strip()) or v.name
