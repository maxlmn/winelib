"""A bottle from photos of its labels (the front, and the back if there's one): Claude reads what's printed on them
(producer, cuvée, vintage, appellation, colour, size, disgorgement), then the reading is matched against the database
as Fill from text's is. For the bottle form's "Fill from photos": a draft to check, nothing saved.

Needs an Anthropic API key: ANTHROPIC_API_KEY in .secrets.env (the photos go to Anthropic). The model is
claude-opus-5-5 unless LABEL_MODEL says another.
"""
import base64
import json
import os
import re
from datetime import date

from tasks.from_link import known_cuvee, read_name
from tasks.import_cellar import Lookup
from tasks.import_scores import COLOURS
from tasks.matching import norm

MODEL = "claude-opus-5-5"
MEDIA_TYPES = ("image/jpeg", "image/png", "image/webp")
MAX_BYTES = 5 * 1024 * 1024  # a photo, as sent (the form shrinks them to ~1600 px first)
SIDES = ("front", "back")
TYPES = ["Red", "White", "Bubbles", "Bubbles Rose", "Rose", "Sweet", "Orange", "Fortified"]
SIZES = ["75cl", "37.5cl", "150cl", "300cl", "600cl"]
FIELDS = ("producer", "cuvee", "vintage", "appellation", "colour", "size", "disgorgement")

PROMPT = """These are photos of a wine bottle's labels ({sides}). Read what is printed on them for a cellar record.

- producer: the estate or house as the label names it ("Domaine Roulot", "Krug", "Clos Rougeard"), not the importer
  or the bottler's address line unless it is the only name.
- cuvee: the wine's own name if it has one ("Les Perrières", "Grande Cuvée 171ème Édition", "Le Bourg"), without the
  producer, appellation, vintage or colour; "" if the wine is just the appellation.
- vintage: the year, "NV" for a non-vintage wine (e.g. a Champagne with no year), "" if you can't see it. Look at the
  neck label and the back label too.
- appellation: as printed, without "Appellation ... Contrôlée" ("Meursault Premier Cru", "Saumur-Champigny").
- region and country if printed or certain from the appellation.
- colour: one of {types}, or "" if neither the label nor the appellation tells.
- size: one of {sizes} when the volume is printed (75 cl, 750 ml, 1.5 L...), else "".
- disgorgement: a sparkling wine's disgorgement date as printed ("Oct 2024", "2019", "06/2023"), else "".
- grapes: those named on the labels.
- not_read: the fields above you couldn't read or are unsure of.
- note: one short sentence for the person checking, only when useful (e.g. "Vintage read from the neck label",
  "Producer from the back label's bottler line").

Only what is printed or unmistakable: leave a field empty rather than guess. When the front and the back disagree, the
back label's legal text wins for the producer and the appellation."""

SCHEMA = {
    "type": "object",
    "properties": {
        "producer": {"type": "string"},
        "cuvee": {"type": "string"},
        "vintage": {"type": "string"},
        "appellation": {"type": "string"},
        "region": {"type": "string"},
        "country": {"type": "string"},
        "colour": {"type": "string", "enum": [*TYPES, ""]},
        "size": {"type": "string", "enum": [*SIZES, ""]},
        "disgorgement": {"type": "string"},
        "grapes": {"type": "array", "items": {"type": "string"}},
        "not_read": {"type": "array", "items": {"type": "string", "enum": list(FIELDS)}},
        "note": {"type": "string"},
    },
    "required": ["producer", "cuvee", "vintage", "appellation", "region", "country", "colour", "size", "disgorgement",
                 "grapes", "not_read", "note"],
    "additionalProperties": False,
}


def api_key():
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    return key or None


def _photos(photos):
    """The photos as image blocks, the front first: each {side, media_type, data (base64)}."""
    if not photos:
        raise ValueError("Add a photo of the label first")
    if len(photos) > len(SIDES):
        raise ValueError("Two photos at most: the front and the back")
    blocks = []
    for p in sorted(photos, key=lambda p: SIDES.index(p["side"]) if p.get("side") in SIDES else 0):
        if p.get("media_type") not in MEDIA_TYPES:
            raise ValueError("A photo must be a JPEG, PNG or WebP image")
        try:
            raw = base64.b64decode(p.get("data") or "", validate=True)
        except ValueError:
            raise ValueError("A photo couldn't be read")
        if not raw or len(raw) > MAX_BYTES:
            raise ValueError("A photo is empty or too large (5 MB at most)")
        blocks.append({"type": "text", "text": f"The {p.get('side') or 'front'} label:"})
        blocks.append({"type": "image", "source": {"type": "base64", "media_type": p["media_type"],
                                                   "data": base64.standard_b64encode(raw).decode()}})
    return blocks


def read_label(photos):
    """What Claude reads on the labels: a dict of SCHEMA's fields."""
    import anthropic
    key = api_key()
    if not key:
        raise ValueError("Reading labels needs an Anthropic API key: ANTHROPIC_API_KEY in .secrets.env")
    blocks = _photos(photos)
    sides = " and ".join(b["text"].split()[1] for b in blocks if b["type"] == "text")
    prompt = PROMPT.format(sides=sides, types=", ".join(TYPES), sizes=", ".join(SIZES))
    client = anthropic.Anthropic(api_key=key)
    try:
        response = client.beta.messages.create(
            model=os.environ.get("LABEL_MODEL", "").strip() or MODEL,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",  # a model that declines: another reads it
            messages=[{"role": "user", "content": [*blocks, {"type": "text", "text": prompt}]}],
            output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
        )
    except anthropic.AuthenticationError:
        raise ValueError("Anthropic refused the API key (ANTHROPIC_API_KEY in .secrets.env)")
    except anthropic.PermissionDeniedError:
        raise ValueError("The Anthropic API key isn't allowed to use this model")
    except anthropic.RateLimitError:
        raise ValueError("Anthropic's rate limit was reached: try again in a minute")
    except anthropic.BadRequestError as e:
        raise ValueError(f"Anthropic couldn't read the photos: {e.message}")
    except anthropic.APIStatusError as e:
        raise ValueError(f"Anthropic's API failed ({e.status_code}): try again")
    except anthropic.APIConnectionError:
        raise ValueError("Anthropic's API couldn't be reached")
    if response.stop_reason == "refusal":
        raise ValueError("The labels couldn't be read")
    text = next((b.text for b in response.content if b.type == "text"), "")
    try:
        return json.loads(text)
    except ValueError:
        raise ValueError("The labels couldn't be read")


def resolve(session, read):
    """The reading against the database: {producer, cuvee, vintage, type, size, appellation, region, wine_id, like_id,
    disgorgement_date, line, not_read, note, ...} as Fill from text gives (no quantity, price, date or vendor)."""
    lookup = Lookup(session)
    text = lambda k: (read.get(k) or "").strip()  # noqa: E731
    producer = None
    if text("producer"):
        p, _ = lookup.producers.named(text("producer"))
        producer = {"id": p.id, "name": p.name} if p else {"id": None, "name": text("producer")}
    r = lookup.region(text("region"), text("country")) if text("region") or text("country") else None
    region = {"id": r.id, "name": r.name} if r else None
    appellation = None
    if text("appellation"):
        a = lookup.appellation(text("appellation"), r)
        if a is not None:
            appellation = {"id": a.id, "name": a.name}
            region = {"id": a.region_obj.id, "name": a.region_obj.name} if a.region_obj else region
        else:  # "Appellation Chablis Contrôlée", "Saumur-Champigny Rouge": the longest run that names one
            named = read_name(text("appellation"), lookup)
            appellation, region = named["appellation"], named["region"] or region
    vintage = text("vintage")
    year = re.fullmatch(r"(19|20)\d\d", vintage)
    vintage = vintage if year and int(vintage) <= date.today().year + 1 else "NV" if norm(vintage) in ("nv", "non vintage") else ""
    out = {
        "producer": producer, "cuvee": text("cuvee"), "vintage": vintage,
        "type": COLOURS.get(norm(text("colour"))), "size": text("size") if text("size") in SIZES else None,
        "appellation": appellation, "region": region,
        "wine_id": None, "like_id": None,
    }
    out = known_cuvee(session, out)
    disgorged = text("disgorgement") or None
    if out["wine_id"] and disgorged:
        out = _disgorgement(session, out, disgorged)
    line = " ".join(x for x in [(producer or {}).get("name"), out["cuvee"], (appellation or {}).get("name"), vintage] if x)
    return {**out, "line": line, "disgorgement_date": disgorged,
            "not_read": [f for f in read.get("not_read") or [] if f in FIELDS], "note": text("note") or None,
            "qty": None, "price": None, "currency": None, "price_total": None, "purchase_date": None, "vendor": None}


def _disgorgement(session, out, disgorged):
    """Each disgorgement of a wine is its own (an NV's "NV - Oct 2024"): the one with the label's date, else a new one
    of the wine found (its `like_id`)."""
    from models import Wine
    w = session.get(Wine, out["wine_id"])
    same = [x for x in session.query(Wine).filter(Wine.producer_id == w.producer_id, Wine.cuvee == w.cuvee,
                                                  Wine.vintage == w.vintage, Wine.type == w.type)
            if norm(x.disgorgement_date or "") == norm(disgorged)]
    return {**out, "wine_id": same[0].id} if same else {**out, "wine_id": None, "like_id": w.id}


def from_photos(session, photos):
    return resolve(session, read_label(photos))
