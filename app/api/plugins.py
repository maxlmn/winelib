"""Plug-ins: extras that aren't part of the app (a scraper for a site you subscribe to, an export to your notes...).

A plug-in is a Python package in PLUGINS_DIR (default: the checkout's plugins/, mounted into the container), whose
`register(api)` adds what it brings through `api` (an Api):
- routers: its own endpoints, under /api/plugins/<name>/ by convention;
- wine actions: buttons on the wine page, declared as data (the page is built into the image, a plug-in can't bring
  page code). `GET /api/wines/{id}` lists those that apply to the wine; the page calls the endpoint (POST) and shows
  the answer's `message`, reloading the wine when it says `reload`;
- Maintenance tasks and groups (routers/maintenance.py: same shape as TASKS).

The app works fully without any. A plug-in that fails to load is logged and left out (GET /api/plugins says why).
"""
import importlib
import logging
import os
import sys
import types
from dataclasses import dataclass
from typing import Callable

from fastapi import APIRouter

import paths

log = logging.getLogger(__name__)
PLUGINS_DIR = paths.PLUGINS_DIR
PACKAGE = "winelib_plugins"  # the plug-ins are imported as winelib_plugins.<name> (relative imports work)


@dataclass
class WineAction:
    id: str
    label: str
    endpoint: str  # "{id}" is the wine's
    critic: str | None = None  # drawn on that critic's line of the Critics card (else with the card's own buttons)
    busy: str | None = None  # shown while it runs ("Searching… about 20 s")
    confirm: str | None = None  # asked first
    show: Callable | None = None  # show(wine) -> bool: whether it applies to this wine (always, when None)
    plugin: str = ""

    def public(self, wine):
        return {"id": self.id, "label": self.label, "endpoint": self.endpoint.format(id=wine.id), "critic": self.critic,
                "busy": self.busy, "confirm": self.confirm}


actions: list[WineAction] = []
loaded: list[dict] = []  # {"name", "ok", "error"}


class Api:
    """What a plug-in's register(api) can add."""

    def __init__(self, app, name):
        self.app = app
        self.name = name

    def include_router(self, router: APIRouter):
        self.app.include_router(router)

    def wine_action(self, id, label, endpoint, *, critic=None, busy=None, confirm=None, show=None):
        actions.append(WineAction(id, label, endpoint, critic, busy, confirm, show, self.name))

    def maintenance_group(self, name, before=None):
        """A group of Maintenance cards, before `before` (one of the app's groups), else last."""
        from routers import maintenance
        if name in maintenance.GROUPS:
            return
        at = maintenance.GROUPS.index(before) if before in maintenance.GROUPS else len(maintenance.GROUPS)
        maintenance.GROUPS.insert(at, name)

    def maintenance_task(self, id, **task):
        """A Maintenance card: group, title, description, fn(session, job), preview, writes, and optionally limit,
        unit, hidden, params(body, commit) -> the job's params (raising HTTPException for a bad request)."""
        from routers import maintenance
        if task.get("group") not in maintenance.GROUPS:
            self.maintenance_group(task.get("group") or self.name)
        maintenance.TASKS[id] = task


def load(app, folder=PLUGINS_DIR):
    """Imports every package in the folder and calls its register(api)."""
    if not folder or not os.path.isdir(folder):
        return
    package = sys.modules.get(PACKAGE)
    if package is None:
        package = types.ModuleType(PACKAGE)
        package.__path__ = []
        sys.modules[PACKAGE] = package
    if folder not in package.__path__:
        package.__path__.append(folder)
    for name in sorted(os.listdir(folder)):
        if name.startswith((".", "_")) or not os.path.isfile(os.path.join(folder, name, "__init__.py")):
            continue
        try:
            module = importlib.import_module(f"{PACKAGE}.{name}")
            module.register(Api(app, name))
            loaded.append({"name": name, "ok": True, "error": None})
            log.info("Plug-in %s loaded", name)
        except Exception as e:
            log.exception("Plug-in %s couldn't be loaded", name)
            loaded.append({"name": name, "ok": False, "error": f"{type(e).__name__}: {e}"})


def wine_actions(wine):
    """The wine actions that apply to this wine."""
    out = []
    for a in actions:
        try:
            if a.show is None or a.show(wine):
                out.append(a.public(wine))
        except Exception:
            log.exception("Plug-in %s: wine action %s", a.plugin, a.id)
    return out


router = APIRouter()


@router.get("/api/plugins")
def list_plugins():
    return {"folder": PLUGINS_DIR, "plugins": loaded}
