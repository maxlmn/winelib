import os

# How WineLib introduces itself to the services it asks (OpenStreetMap, Bordeaux Index, WineLabs, Wikidata, VIVC):
# their usage policies ask for an identifying User-Agent
USER_AGENT = os.getenv("WINELIB_USER_AGENT") or "WineLib/1.0 (self-hosted wine cellar app)"
