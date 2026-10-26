# WineLib

**Your wine cellar and tasting journal, on maps.** WineLib keeps your bottles, where they sit and what they're
worth, every wine you've tasted and where, and puts them on the map of the world's appellations, down to the
vineyard. It runs on your own computer: your data stays yours.

![A wine with its appellation and vineyard on the map](screenshots/wine.png)

## What it does

**The maps.** Every appellation of France (INAO), the EU, the US and Australia outlined, and Burgundy's premiers
crus; regions in their colours, your cellar and your tastings on them. A wine page shows its appellation and
vineyard; a region's page, where what you drink comes from.

![A region: its map, what you drink from it](screenshots/map.png)

**Draw what the map doesn't have.** A lieu-dit, a monopole, an appellation without an official outline: draw it on
the satellite view, start from the official outline and refine it, or import a GeoJSON or KML file.

![Drawing an outline over the satellite view](screenshots/draw.png)

**The cellar map.** Your shelves bin by bin, filled against their capacity and coloured by region; click a bin to
see what's in it. Cards, a list, a vintage chart, prices and their changes.

![The shelf map](screenshots/cellar.png)

**The tasting journal.** Tastings by occasion (a dinner, a restaurant, a trip), with your notes, ratings, photos and
the places on a map; trends over the years.

![Tasting cards by occasion](screenshots/tastings.png)

**The grapes' family.** 635 grapes with their colour, origin and parents (from VIVC, the Vitis International Variety
Catalogue): a network of every known parent → offspring link, your wines on it, and each grape's family tree.

![The grape family network](screenshots/grapes.png)

![A grape: its profile, its family](screenshots/grape.png)

And more:

- **A complete reference**: 129 wine regions, 2,900 appellations (every INAO name, AVA, EU PDO and PGI, and eight
  other countries' official registers), 635 grapes with their synonyms, ready on the first start.
- **A wine's grapes and blend**: a list of grapes with their share, a blend style (Bordeaux, Rhône, Champagne, field
  blend), filters that find a grape in any blend.
- **Vintages**, **producers**, **places** and **summary** pages; ⌘K search everywhere.
- **Critics' scores** from any critic (a CSV of reviews), shown together.
- **Market prices** by LWIN, from Bordeaux Index or WineLabs (with your own keys).
- **Imports** from CellarTracker, Vivino or any spreadsheet; **export** of everything as JSON or CSV.
- **Plug-ins** for your own extras: their pages, Maintenance tasks and actions on the wine page.

## Quick start

With Python 3.11 or newer, download the zip of the latest release (GitHub › Releases), unzip it, then:

```bash
pip install -r app/api/requirements.txt
python run.py
```

It opens http://127.0.0.1:8000 on a short setup page (your currency, where you keep bottles, your preferred critic). Your data lives
in your user folder (`%APPDATA%\winelib`, `~/Library/Application Support/winelib` or `~/.local/share/winelib`;
`--data` for another), apart from the program, so a newer version finds it.

Then, in Settings › Maintenance:

- **Map outlines** downloads the appellations' outlines (the map pack);
- **Import a cellar** brings your CellarTracker or Vivino export, or your spreadsheet.

WineLib is reachable from your computer only. `--host 0.0.0.0` opens it to your network: only behind your own
sign-in (Tailscale, a proxy with login), never exposed bare. Docker and Postgres are options (`docker/`, `DB_URL`).

From the source: Node.js to build the web app once (`cd app/web && npm install && npm run build`), then as above.

## The data and its sources

The reference data and the map come from official, open sources (INAO, the EU's eAmbrosia register, UC Davis's AVA
project, Wine Australia, Wikidata, VIVC, Natural Earth...), each credited in the app (Settings › About the data) and
in [`app/api/data/docs/sources.md`](app/api/data/docs/sources.md).

## Licence

[MIT](LICENSE). The data keeps its own licences (see above).
