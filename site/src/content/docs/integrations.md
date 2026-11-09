---
title: Integrations
description: The optional services WineLib can use with your own keys.
---

Everything here is optional: WineLib works fully without any of it. Each service needs your own key, set in
`.secrets.env` next to `run.py` (copy
[`.secrets.env.example`](https://github.com/maxlmn/winelib/blob/main/.secrets.env.example)), or as an `environment:`
entry in `docker-compose.yml`. **Settings › Integrations** shows which are set up.

| Service | What it adds | What it needs |
|---|---|---|
| **Esri World Imagery** | The satellite view outside France. Without it, Satellite is IGN's photos in France and the plain map elsewhere. | `ESRI_API_KEY`, from a free [ArcGIS Location Platform](https://location.arcgis.com) account (about 2 million map tiles a month free). Your browser uses the key: on Esri's site, limit it to World Imagery and your WineLib's address. |
| **Anthropic (Claude)** | *Fill from photos*: a new bottle from photos of its labels. The photos are sent to Anthropic. | `ANTHROPIC_API_KEY`, from [console.anthropic.com](https://console.anthropic.com). Billed to your key, about a cent or two a bottle. |
| **WineLabs.ai** | Market prices for bottles with an LWIN code. | `WINELABS_API_KEY`. |
| **Bordeaux Index** | Your Bordeaux Index portfolio beside your bottles held there, and market prices from LiveTrade. | An approved LiveTrade API access: `BI_EMAIL`, `BI_PASSWORD`, `BI_SALES_LEDGER`, `BI_PURCHASE_LEDGER`. |
| **LWIN list** | LWIN suggestions in the wine form (needed for market prices). | Liv-ex's LWIN file, indexed once (`python app/api/tasks/match_lwin.py --build-index`) and copied to `data/lwin/`. |

## Your AI assistant

The MCP server lets Claude, or any assistant that speaks MCP, read your cellar, journal and lists, and log wines and
tastings after your yes. It needs no key from WineLib's side: see [Ask your AI assistant](../mcp/).
