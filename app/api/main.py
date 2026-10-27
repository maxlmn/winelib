"""WineLib API. Run from app/api:  uvicorn main:app --reload"""
import importlib
import logging
import mimetypes
import os
import pkgutil
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import geo
import migrate
import plugins
import reference
import routers
from db import engine

# The installable app's manifest (app/web/static): not in every system's list of types
mimetypes.add_type("application/manifest+json", ".webmanifest")

# The app's own messages (reference updates, the maps...) next to uvicorn's, which keeps its own handlers
logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s: %(message)s")

@asynccontextmanager
async def lifespan(app):
    migrate.upgrade(engine)  # the schema the code expects (migrations/): before anything reads the database
    reference.seed(engine)  # a new, empty database: regions, appellations, grapes, vineyards (app/api/data/reference/)
    reference.update(engine)  # what a newer version ships, by stable key (never overwriting, never re-adding)
    # The shape store is read once in the background, not on the first map request
    threading.Thread(target=geo.warm, name="warm-geo", daemon=True).start()
    yield


app = FastAPI(title="WineLib API", lifespan=lifespan)
# Map shapes are mostly coordinates: gzip shrinks them ~4x. Level 5 is nearly as small as 9, several times faster
app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=5)


@app.get("/api/health")
def health():
    return {"ok": True}


# Mount every routers/<area>.py that defines `router`
for module in sorted(m.name for m in pkgutil.iter_modules(routers.__path__)):
    mod = importlib.import_module(f"routers.{module}")
    if hasattr(mod, "router"):
        app.include_router(mod.router)

# Plug-ins (plugins.py): their endpoints, wine actions and Maintenance tasks
app.include_router(plugins.router)
plugins.load(app)


# Serve the built SvelteKit app (app/web/build) with SPA fallback, so one container serves everything
WEB_BUILD = os.getenv("WEB_BUILD", os.path.join(os.path.dirname(__file__), "..", "web", "build"))
if os.path.isdir(WEB_BUILD):
    app.mount("/_app", StaticFiles(directory=os.path.join(WEB_BUILD, "_app")), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "Not found")
        file = os.path.join(WEB_BUILD, path)
        if path and os.path.isfile(file):
            return FileResponse(file)
        return FileResponse(os.path.join(WEB_BUILD, "index.html"))
