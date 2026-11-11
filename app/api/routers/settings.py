"""Settings page: exchange rates, local totals, Bordeaux Index, storage groups, map defaults, links."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import settings
from db import Appellation, get_session

router = APIRouter()


@router.get("/api/settings")
def get_settings(session: Session = Depends(get_session)) -> settings.Settings:
    return settings.load(session)


@router.get("/api/settings/setup")
def setup(session: Session = Depends(get_session)):
    """{"needed": true} until settings are saved once (the first-start page)."""
    return {"needed": not settings.saved(session)}


@router.get("/api/integrations")
def integrations(session: Session = Depends(get_session)):
    """The optional connections and what each needs: the page shows those configured (Bordeaux Index's tab and
    settings) and explains the others. Keys are read from the environment (.secrets.env)."""
    import os
    import map_pack
    import plugins
    from tasks import bordeaux_index, from_photos, match_lwin
    from tasks import update_market_prices as prices
    return {
        "integrations": [
            {"id": "bordeaux_index", "name": "Bordeaux Index", "configured": bordeaux_index.configured(),
             "what": "Your Bordeaux Index portfolio next to your bottles held there (the cellar's Bordeaux Index tab), "
                     "and market prices from it and its LiveTrade market.",
             "needs": "An approved LiveTrade API access: BI_EMAIL, BI_PASSWORD, BI_SALES_LEDGER, BI_PURCHASE_LEDGER "
                      "in .secrets.env."},
            {"id": "winelabs", "name": "WineLabs.ai", "configured": bool(prices.api_key()),
             "what": "Market prices for bottles with an LWIN (the bottle page's button, Maintenance › Market prices).",
             "needs": "An API key: WINELABS_API_KEY in .secrets.env."},
            {"id": "anthropic", "name": "Anthropic (Claude)", "configured": bool(from_photos.api_key()),
             "what": "Fill from photos in the bottle form: the labels' photos (front and back) read by Claude. The "
                     "photos are sent to Anthropic; billed to your key (about a cent or two a bottle).",
             "needs": "An API key from console.anthropic.com: ANTHROPIC_API_KEY in .secrets.env."},
            {"id": "esri", "name": "Esri World Imagery", "configured": bool(esri_key()),
             "what": "The satellite view outside France (IGN's photos cover France without a key; elsewhere the map "
                     "stays plain). Your browser asks Esri for the photos with the key: on Esri's site, limit it to "
                     "World Imagery and your WineLib's address. Esri's free tier is about 2 million tiles a month.",
             "needs": "An ArcGIS Location Platform API key (location.arcgis.com, free account): ESRI_API_KEY in "
                      ".secrets.env."},
            {"id": "lwin", "name": "LWIN list", "configured": os.path.exists(match_lwin.LWIN_DB),
             "what": "LWIN suggestions in the wine form and Maintenance › LWIN codes (needed for market prices).",
             "needs": "Liv-ex's LWIN file, indexed on a PC (python app/api/tasks/match_lwin.py --build-index) and "
                      "copied to data/lwin/."},
        ],
        "plugins": plugins.loaded,
        "map_credits": map_pack.credits(),  # the installed map outlines' licences and credits
        # whether the maps have outlines at all: from the map pack, or a shape store built by hand (which has no
        # credits) or drawn: an appellation linked to one
        "outlines": session.query(Appellation.id).filter(Appellation.boundary.isnot(None), Appellation.boundary != "").first() is not None,
        # Esri's terms want a key for World Imagery; the browser fetches the tiles, so it gets the key (only this one)
        "esri_key": esri_key() or None,
    }


def esri_key():
    import os
    return os.environ.get("ESRI_API_KEY", "").strip()


@router.get("/api/settings/defaults")
def default_settings() -> settings.Settings:
    return settings.Settings()


@router.put("/api/settings")
def put_settings(body: settings.Settings, session: Session = Depends(get_session)) -> settings.Settings:
    return settings.save(session, body)
