"""Each appellation's details say what it is (docs/reference-data.md; run after appellations.py).

The details start with its classification: "DOCG", "AOP", "Complementary geographic name of Coteaux du Layon",
"IGP", "AVA", "DO (Denominación de Origen)", "PDO" for an EU row that says no more... (from its type, or its EU id
when the type is only the product category: "Wine", "Quality Sparkling Wine/Wine"). What the details said that's
worth keeping follows ("DOCG · Verona", "AVA · Napa Valley, North Coast"); Winemap's "Imported from Winemap. <EU
link>" (the link is in location_link) and a bare slug ("côte-rôtie") are dropped.

A dry run unless --commit; the report (every change) goes to data/reference_build/details.txt.

    python scripts/reference/details.py            # dry run
    python scripts/reference/details.py --commit   # after a backup
"""
import argparse
import collections
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
REPORT = os.path.join(ROOT, "data", "reference_build", "details.txt")
SEP = " · "

# A type -> how the details name it (types not listed are said as they are: DOC, DOCG, AOP, AVA, DAC...)
LABELS = {
    "Denomination": "Complementary geographic name",
    "Mention": "Premier cru mention",
    "IGP": "IGP (Indication Géographique Protégée)",
    "IGT": "IGT (Indicazione Geografica Tipica)",
    "DO": "DO (Denominación de Origen)",
    "DOCa": "DOCa (Denominación de Origen Calificada)",
    "VT": "Vino de la Tierra (PGI)",
    "VC": "Vino de Calidad con Indicación Geográfica",
    "Vino de Pago": "Vino de Pago",
    "AVA": "AVA (American Viticultural Area)",
    "Wine Region": "Australian GI (Geographical Indication)",
    "Ward": "Wine of Origin ward",
    "District": "Wine of Origin district",
    "Geographical units": "Wine of Origin geographical unit",
    "National": "National appellation",
    "Landwein": "Landwein (PGI)",
    "Vinho Regional": "Vinho Regional (PGI)",
    "GI": "GI (Geographical Indication)",
    "Sub-GI": "Sub-GI (Geographical Indication)",
    "DVA": "DVA (VQA Designated Viticultural Area)",
    "Sub-appellation": "VQA sub-appellation",
    "IG": "IG (Indicación Geográfica)",
    "Appellation of Origin": "Appellation of Origin",
    "AOC (canton)": "AOC (cantonal)",
    "State": "State",
    "County": "County",
}
# Each country's generic appellation (filed under its country: docs/reference-data.md)
NATIONAL = {"Vin de France", "Vino d'Italia", "Vino de España", "Deutscher Wein", "Landwein", "Vinho de Portugal",
            "Österreichischer Wein"}
# A type that means one thing in one country and another elsewhere
BY_COUNTRY = {("Region", "Germany"): "Anbaugebiet", ("Region", "South Africa"): "Wine of Origin region",
              ("Region", "Chile"): "DO region", ("Subregion", "Chile"): "DO subregion", ("Zone", "Chile"): "DO zone",
              ("Area", "Chile"): "DO area", ("DOC", "Argentina"): "DOC (Denominación de Origen Controlada)",
              ("GI", "Japan"): "GI (Japan, National Tax Agency)"}
# Types that are only the EU product category (Winemap's): the EU id says what it is
CATEGORY = re.compile(r"^(?:[A-Za-z -]*(?:Wine|Must|Grapes)[A-Za-z -]*/?)+$")


def classification(a):
    """What the appellation is, as the details' first words; None when nothing says."""
    kind = (a.type or "").strip()
    country = a.region_obj.country if a.region_obj else None
    if a.name in NATIONAL:
        return "National appellation"
    if kind and (kind in LABELS or (kind, country) in BY_COUNTRY or not CATEGORY.match(kind)):
        label = BY_COUNTRY.get((kind, country)) or LABELS.get(kind, kind)
        if kind == "Denomination" and a.subregion:
            label += f" of {a.subregion}"
        return label
    pdo = (a.pdo_id or "").upper()
    if pdo.startswith("PDO"):
        return "AOP" if country == "France" else "PDO (EU protected designation of origin)"
    if pdo.startswith("PGI"):
        return "IGP (Indication Géographique Protégée)" if country == "France" else "PGI (EU protected geographical indication)"
    return None


def kept(a, label):
    """The part of the current details worth keeping."""
    text = (a.details or "").strip()
    if not text or text.startswith("Imported from Winemap"):
        return ""
    if text == text.lower() and re.fullmatch(r"[a-zà-ÿœæ0-9'’ -]+", text):  # a slug: côte-rôtie, alsace ou vin-d'alsace
        return ""
    for prefix in (label, label.split(" (")[0]) if label else ():  # already says it: "AVA (...) · Lodi", "DAC (for ...)"
        if text == prefix:
            return ""
        if text.startswith(prefix + SEP):
            return text[len(prefix + SEP):].strip()
        if text.startswith(prefix + " (") and text.endswith(")"):
            return text[len(prefix + " ("):-1].strip()
    if text.upper() in {(a.type or "").upper(), "DAC", "AVA", "AOP", "DOC", "DOCG"}:
        return ""
    return text


def plan(session):
    from winelib_utils.models import Appellation
    changes, unknown = [], []
    for a in session.query(Appellation).order_by(Appellation.name):
        label = classification(a)
        rest = kept(a, label)
        new = SEP.join(x for x in (label, rest) if x) or None
        if new != (a.details or None):
            changes.append((a, a.details, new))
        if not label:
            unknown.append(a)
    return {"changes": changes, "unknown": unknown}


def report(p):
    out = ["Appellation details (docs/reference-data.md)", "",
           f"Details changed: {len(p['changes'])}"]
    by_label = collections.defaultdict(list)
    for a, old, new in p["changes"]:
        by_label[(new or "").split(SEP)[0]].append((a, old, new))
    for label, rows in sorted(by_label.items(), key=lambda kv: -len(kv[1])):
        out.append(f"  {label or '(emptied)'} ({len(rows)})")
        out += [f"    {a.name}: {(old or '').strip()[:70]!r} -> {new!r}" for a, old, new in rows[:12]]
        if len(rows) > 12:
            out.append(f"    ... and {len(rows) - 12} more")
    out += ["", f"Nothing says what they are (type and EU id empty): {len(p['unknown'])}"]
    out += [f"  {a.name} ({a.region_obj.name if a.region_obj else '?'}): type {a.type!r}" for a in p["unknown"]]
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--commit", action="store_true", help="write (take a backup first); without it, a dry run")
    args = parser.parse_args()
    import config
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    session = sessionmaker(bind=create_engine(config.DB_URL))()
    try:
        p = plan(session)
        os.makedirs(os.path.dirname(REPORT), exist_ok=True)
        with open(REPORT, "w", encoding="utf-8") as f:
            f.write("\n".join(report(p)) + "\n")
        print(f"{len(p['changes'])} details changed; {len(p['unknown'])} without a classification. "
              f"Report: {os.path.relpath(REPORT, ROOT)}")
        if args.commit:
            for a, _, new in p["changes"]:
                a.details = new
            session.commit()
            print("Saved.")
        else:
            print("Dry run: nothing saved (--commit to save).")
    finally:
        session.close()


if __name__ == "__main__":
    main()
