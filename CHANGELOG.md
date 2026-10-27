# Changelog

## Unreleased

- **Wine list**: the cellar, or a selection from its filters, laid out like a restaurant's list (sparkling to
  sweet, by region and appellation, a cuvée's vintages on one line, no prices), to print or save as a PDF.
- **Lists**: wines to find and taste (a critic's top 100, a classification, your wishlist); entries are wines,
  cuvées (any vintage) or producers, mixed, each ticked once tasted, sorted by note (ranks, tiers); on the wine and
  producer pages; printed as a wine list or a checklist. The wishlist is one of them (☆ Wishlist on a wine's page).
- **Fill a wine from a link**: a shop's or Vivino's page fills the new wine's fields.
- **Installable on a phone** (Add to Home Screen).
- **An MCP server**: Claude or another assistant reads your cellar, journal and lists (app/mcp_server).
- The README opens on a short demo clip.

## v0.1.0

The first public release: your wine cellar and tasting journal, on maps, running on your own computer.

- **Maps**: every appellation of France (INAO), the EU, the US and Australia outlined, Burgundy's premiers crus,
  regions in their colours; your cellar and tastings on them. Draw or import an outline the map doesn't have.
  The outlines come as a map pack, downloaded from Settings › Maintenance.
- **Cellar**: each storage place as a wine rack (a bottle end per bottle, in its region's colour, the wine's colour
  as the cork), a shelf map bin by bin, a list, a vintage chart, market prices and their changes.
- **Tasting journal**: tastings by occasion with notes, ratings, photos and places; every wine in one line of
  region colours; trends.
- **Summary**: your best-scored wines, the places you go back to, the busiest evening; breakdowns by region,
  colour, producer, appellation, grape and vintage.
- **Grapes**: 635 grapes with colour, origin and parents (VIVC), a family network and each grape's family tree.
- **A complete reference** on the first start: 129 regions, 2,900 appellations, 635 grapes, 2,458 producers.
- **Imports** from CellarTracker, Vivino or a spreadsheet; critics' scores from a CSV; **export** of everything.
- **⌘K search**, light and dark themes in nine palettes, a phone layout.
- **Install**: Docker (`docker compose up -d`, image `ghcr.io/maxlmn/winelib`) or Python (`python run.py`).
