"""The outline on a wine's drawn label (label_shape.py)."""
import json
from types import SimpleNamespace

import label_shape


def _square(x, y, size):
    return [[x, y], [x + size, y], [x + size, y + size], [x, y + size], [x, y]]


def test_a_shape_is_fitted_in_the_box():
    d = label_shape._path(json.dumps({"type": "Polygon", "coordinates": [_square(4.0, 47.0, 0.1)]}))
    assert d.startswith("M") and d.endswith("Z")
    nums = [float(n) for n in d.replace("M", " ").replace("L", " ").replace("Z", " ").split()]
    assert min(nums) >= 0 and max(nums) <= label_shape.BOX


def test_specks_are_left_out():
    shape = {"type": "MultiPolygon", "coordinates": [[_square(4.0, 47.0, 1.0)], [_square(6.0, 47.0, 0.01)]]}
    assert label_shape._path(json.dumps(shape)).count("M") == 1


def test_no_outline_means_no_shape(monkeypatch):
    monkeypatch.setattr(label_shape.geo, "shape", lambda kind, obj: (None, None))
    monkeypatch.setattr(label_shape.geo, "region_outline", lambda name: (None, None))
    wine = SimpleNamespace(appellation=SimpleNamespace(), region_obj=SimpleNamespace(name="Nowhere"))
    assert label_shape.of_wine(wine) is None


def test_the_region_when_the_appellation_has_no_outline(monkeypatch):
    square = json.dumps({"type": "Polygon", "coordinates": [_square(4.0, 47.0, 0.5)]})
    monkeypatch.setattr(label_shape.geo, "shape", lambda kind, obj: (None, None))
    monkeypatch.setattr(label_shape.geo, "region_outline", lambda name: (square, None))
    wine = SimpleNamespace(appellation=SimpleNamespace(), region_obj=SimpleNamespace(name="Bourgogne"))
    assert label_shape.of_wine(wine)["of"] == "region"
