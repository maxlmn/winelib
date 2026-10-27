# Changelog

## Unreleased

- **What happened to a bottle**: gifted, sold (and for how much), broken or otherwise, not only drunk. "Take some
  out" on a bottle's page takes them off the count, with a date and a note; the bottle page tells its story (drunk,
  gifted...), and each can be undone.
- **Find in the lists**: a list, a wine or a note across every list (the matching bottle ends stay bright), and in a
  list its entries by name, note, appellation or region.
- **Faster maps**: every map opens where it's going and draws its outlines without waiting for the background's
  tiles; the home page's map opens on the region of your latest tasting.
- The producer page shows its lists once; the wines' legend wraps on a phone; the wine list's From stays in its card.

## v0.2.0

Lists to taste through, a new home page, a wine list to print and your tastings as stickers for a story.

- **Lists, a treasure hunt**: wines to find and taste (a critic's top 100, Noble Rot's wines of the decade, the 1855
  classification, your wishlist). An entry is a wine, a cuvée (any vintage) or a producer, mixed, and ticks itself
  once you've tasted it. Each list is a mosaic of bottle ends that fills in, in its regions' colours, as you go:
  hover one for the wine, sort them all (the list's order, by note, tasted first, by region). Grey out what you've
  tasted or own; sort a list by its notes (ranks, tiers). The wishlist is one of them (☆ Wishlist on a wine's page).
- **On the wine and producer pages**: the lists naming them, and beside each vintage the critic's score as a pill
  and a mark when it's on a list.
- **A new home page**: the map of the regions you drink, your latest tastings, the past year in one line of colours,
  what to open tonight (the bottles your lists are waiting for first, then those to drink soon) and your latest
  purchases as the cellar's racks, with their prices and where they were bought.
- **A wine list to print**: the cellar, a selection or your bottles from a list, laid out like a restaurant's (by
  colour and region, a cuvée's vintages on one line, no prices), to print or save as a PDF; a whole list as a
  checklist.
- **Share a tasting**: a tasting note or a whole session as a sticker for your Instagram story (transparent, with
  white or dark text, or a card), framed like the journal's cards.
- **Fill a wine from a link**: a shop's or Vivino's page fills the new wine's fields.
- **Installable on a phone** (Add to Home Screen).
- **An MCP server** (app/mcp_server): Claude or another assistant reads your cellar, journal and lists, and makes
  lists for you ("every wine I drank on 3 October", "every note that says wow") once you've said yes.
- The tasting page draws its wines as bottle ends; the lists page loads in a few queries, not one per entry.
- Upgrading: the database is migrated on start (lists, the wishlist moved into them). Back it up first, as always.

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
