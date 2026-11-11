"""A large answer of plain values (thousands of rows), written straight to JSON: FastAPI's generic encoder walks
every value, and on the cellar that was more of the wait than loading it."""
import json
from datetime import date, datetime
from decimal import Decimal

from fastapi import Response


def _plain(value):
    """What a database may hand back besides JSON's own types."""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return str(value)


def fast_json(body):
    return Response(json.dumps(body, ensure_ascii=False, separators=(",", ":"), default=_plain), media_type="application/json")
