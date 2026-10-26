"""Imports every module of the app (app/api, its routers, its tasks) with only the packages installed: run after
`pip install -r app/api/requirements.txt` (CI's fresh-install job), it fails on a package the release doesn't list.

    python scripts/check_imports.py
"""
import glob
import importlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = os.path.join(ROOT, "app", "api")
sys.path[:0] = [API, ROOT]


def modules():
    for folder in ("", "routers", "tasks", os.path.join("tasks", "housekeeping")):
        for path in sorted(glob.glob(os.path.join(API, folder, "*.py"))):
            yield os.path.relpath(path, API)[:-3].replace(os.sep, ".")


failed = []
for name in modules():
    if name.endswith("__init__"):
        continue
    try:
        importlib.import_module(name)
    except ImportError as e:
        failed.append(f"{name}: {e}")
print("\n".join(failed) or "Every module imports.")
sys.exit(1 if failed else 0)
