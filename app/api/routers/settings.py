"""Settings page: exchange rates, local totals, Bordeaux Index, storage groups, map defaults, links."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import settings
from db import get_session

router = APIRouter()


@router.get("/api/settings")
def get_settings(session: Session = Depends(get_session)) -> settings.Settings:
    return settings.load(session)


@router.get("/api/settings/setup")
def setup(session: Session = Depends(get_session)):
    """{"needed": true} until settings are saved once (the first-start page)."""
    return {"needed": not settings.saved(session)}


@router.get("/api/integrations")
def integrations():
    """The optional connections and what each needs: the page shows those configured (Bordeaux Index's tab and
    settings) and explains the others. Keys are read from the environment (.secrets.env)."""
    import os
    import map_pack
    import plugins
    from winelib_utils import bordeaux_index, match_lwin
    from winelib_utils import update_market_prices as prices
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
            {"id": "lwin", "name": "LWIN list", "configured": os.path.exists(match_lwin.LWIN_DB),
             "what": "LWIN suggestions in the wine form and Maintenance › LWIN codes (needed for market prices).",
             "needs": "Liv-ex's LWIN file, indexed on a PC (python winelib_utils/match_lwin.py --build-index) and "
                      "copied to data/lwin/."},
        ],
        "plugins": plugins.loaded,
        "map_credits": map_pack.credits(),  # the installed map outlines' licences and credits
    }


@router.get("/api/settings/defaults")
def default_settings() -> settings.Settings:
    return settings.Settings()


@router.put("/api/settings")
def put_settings(body: settings.Settings, session: Session = Depends(get_session)) -> settings.Settings:
    return settings.save(session, body)
