"""fastjson.fast_json: a large answer written straight to JSON, with what a database may hand back."""
import json
from datetime import date
from decimal import Decimal

from fastjson import fast_json


def test_dates_and_decimals_are_json_values():
    r = fast_json({"price": Decimal("85.50"), "day": date(2024, 1, 15), "name": "Côte-Rôtie", "none": None})
    assert r.media_type == "application/json"
    assert json.loads(r.body) == {"price": 85.5, "day": "2024-01-15", "name": "Côte-Rôtie", "none": None}
