# Changelog

## v0.3.3

- A clicked lieu-dit's card stays open while the pointer crosses others on the way to its button.
- Lieux-dits: a name the cadastre uses for several places apart in one village (a field name, "Grande Pièce") is as
  many lieux-dits, no longer one scattered over the village (the map pack's lieux-dits rebuilt).

## v0.3.2

- On a phone's full-size map, a lieu-dit's card sits above the page, no longer under the map's controls.
- The cadastre's unnamed places (what's left between the lieux-dits, some large) are no longer shown as lieux-dits.

## v0.3.1

- A full-size map on a phone keeps the bar and its menu above it; no more placeholder where the map was.

## v0.3.0

- **Lieux-dits**: the cadastre's named places among the vines (Loire, Burgundy, Beaujolais, Jura, Alsace, Bordeaux,
  Rhône), with their eligible appellations, on the map from close zoom. Hover one for its name and village, click it
  to make it the wine's vineyard; Settings › Maintenance › *Lieux-dits for your wines* finds the cuvées named after
  one ("Les Poyeux") and links them after your tick; the wine form's vineyard picker offers them too. A lieu-dit's
  page says how much of it is in AOC vines. Needs the map pack's new `lieu_dit` store.
- **Full-size maps**: ⤢ on a page's map fills the window, the page a column of cards over it (a sheet you scroll on
  a phone); Esc or *Back to the page* returns. Settings › Appearance › Maps can make it the default. The map credits
  now fold into an ⓘ.
- **Faster, cleaner maps**: the Plain map is drawn from OpenFreeMap's vector tiles in WineLib's own muted style (a
  light and a dark one, vineyards faintly tinted), drawn in about a second where it took two to three;
  OpenStreetMap France's tiles stay as the fallback. Satellite shows IGN's aerial photos in France (sharper and
  newer), Esri's elsewhere.
- **Lists from criteria**: a new list filled from your wines matching tags, colours, regions, grapes, vintages, in
  the cellar or tasted, your rating or words in the name, with how many match as you pick. Made once (they become
  its entries) or **live** (it keeps the criteria and shows whatever matches today: a wine tagged tomorrow joins it).
  Through Claude too: "make me a live list of my fresh Loire whites" (`create_list` with criteria, `find_wines`).
- **Style tags**: a wine's style in a few words (fresh, mineral, full-bodied, for ageing… or your own), set on the
  wine or picked in a tasting; the wine page gathers them (×3 when three tastings found it), the cellar and *What
  should I open?* filter by them ("something fresh tonight"), and the cellar's search finds them. The tasting's
  own tags (Dinner, corked) stay apart: they're the occasion, these are the wine.
- **What happened to a bottle**: gifted, sold (and for how much), broken or otherwise, not only drunk. "Take some
  out" on a bottle's page takes them off the count, with a date and a note; the bottle page tells its story (drunk,
  gifted...), and each can be undone.
- **From a label's photo to WineLib, through your assistant**: the MCP server adds wines, tastings and bottles after
  your yes (`add_wine`, `add_tasting`, `add_bottle`). Share a label's picture with Claude and say what to log: it
  reads the label, matches the producer, appellation and place to yours, shows what it will add and waits for you.
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
