# Changelog

## v0.3.7

- **The Lyonnais in France**: Coteaux du Lyonnais (its wines, their vineyards, the Lyonnais' producers) is filed under
  France, in neither the Rhône (where v0.3.6 had put it) nor the Beaujolais (migration 0009).
- **Region outlines that follow the vineyards**: the Beaujolais is its AOC's area, the Rhône's north (up the valley to
  Côte-Rôtie) and its Gard bank follow its appellations' outlines, with no straight cuts; the two no longer overlap.
  Every region's outline is finer (~250 m, from ~1 km).
- **Finer appellation outlines**: the map pack's outlines twice as fine (~25 m, from 40–60 m); the pack is 73 MB
  (Settings › Maintenance › Map outlines downloads it again). Outlines you draw are simplified the same way.
- **Clicks you can predict**: in the tastings (the journal, a wine's, producer's or bottle's history) each wine's
  note (or *No note*) is shown and opens the tasting; the *Notes inline* switches are gone; a tasting card's date
  opens the occasion in the journal (that day there, every wine poured). In the cellar, a wine's label and bottle ends
  open the bottle. The tasting page says it's one, like the other pages.
- **Map cards**: a shape's card shows its link from the first hover (*Details →*, a lieu-dit's *Its page →* and its
  action); a click keeps the card. No more "Click for details" that only added a link, nor a link to the page you're on.
- **Each appellation and vineyard shown or hidden**: on every page's map, an entry's colour square in the legend
  hides its shape (hollow) or shows it again; its name still zooms to it.
- **A vineyard's map**: a lieu-dit clicked can be made the vineyard's outline (its wines keep it; an outline you drew
  is replaced after asking).
- **A new vintage takes its vineyard**: a new wine without one takes the vineyard its other vintages share.
- A page whose map has nothing to show (an appellation without an outline) no longer opens it full size.
- **Fill from text**: a new bottle from a pasted order or auction email, invoice or producer's sheet: the wine (yours,
  or a new vintage of a cuvée you have), the quantity, the price a bottle (a lot's divided), the date and the vendor.
- **Settings in three tabs**: Settings, Maintenance, and **Needs attention**: what the quick checks find (wines entered twice, records pointing at nothing,
  a vintage under two appellations, market prices not refreshed, cellar wines
  without an LWIN, restaurants without coordinates), its count on the tab, each opening its Maintenance task with
  the preview run.
- **Keeping vintages together** (Settings › Maintenance): *Cuvées under several appellations* finds a vintage entered twice or left under an old name.
- Fixes: *Duplicate wines* missed duplicates whose disgorgement date was empty on one and unset on the other; names
  match "Premier" and "1er" ("Premier Grand Cru Classé" is an auction's "1er Grand Cru Classé"); the map outlines
  that crossed themselves (rounding) are repaired: their fill no longer draws inside out.
- Browser smoke tests (app/web/e2e, `npm run e2e`) in CI: the pages load, and the clicks go where they should.
- The server no longer logs "No response returned" for a page left while it loaded.

## v0.3.6

- **A bottle's page** says what it is in words ("3 bottles", "2 magnums", "1 bottle, finished") with its bottles
  beside the title as bottle ends in the region's colour (those gone faded), and where it sits: "In R19 · Wine room"
  and a mini shelf map of its storage group, each bin filled as far as it holds, its own highlighted (a bin opens
  the cellar's shelf map).
- **France's regions**: the Lyonnais is part of the Rhône (Coteaux du Lyonnais moves there, with its wines,
  producers and the live lists on it; migration 0008); the Rhône's outline reaches up to Lyon (Côte-Rôtie,
  Condrieu, Château-Grillet were outside it) and over the Gard's bank (Tavel, Lirac, Costières de Nîmes); the
  Beaujolais in its own violet, no longer Bourgogne's pink (unless you had changed it), its outline north of Lyon.
- **Security**: the app's pages no longer serve files outside the web build (an address with an encoded "../"
  could read any file the app could, its settings and your plug-ins' logins among them). *Fill a wine from a link*
  no longer fetches local addresses (this machine, the local network), nor follows a redirect to one.
- **Errors you can see**: a save or a load that fails now says why (Settings, a list's entries, a bottle taken out
  or put back, market prices, Maintenance's jobs, the Map page) instead of failing silently or staying on
  "Loading…"; Settings says "Saved" again after a save (it kept saying "Unsaved changes").
- **Fixes**: maps left before they finished loading no longer stay in memory; a list's search no longer shows an
  older, slower answer; photo previews are let go; the lieux-dits are asked again after a failure; a full-size
  map follows a window resized or a phone turned; exchange rates can no longer read as missing while a request
  values the cellar; the map store is read again after a rebuild or a map pack installed while the app runs, and
  a damaged pack leaves the store as it was.
- **Faster**: the lieux-dits looked up by an index and held once in memory (not twice), their search ready at
  startup; a shape's full detail found at once on a large store; Satellite looks only at a tile's edges for IGN's
  blank (most tiles), and falls back to Esri's photo when IGN fails.
- **Releases**: the image is built before the GitHub release is made (a failed image no longer leaves a release
  without it), :latest only for final versions, the MCP server's tests and the web check run first; the
  dependencies kept within their major versions; the schema checked on Postgres in CI, and every migration's
  downgrade tested (the one from the wishlist's move to a list didn't work).

## v0.3.5

- **The lists page**: the cards stack in columns, a short one no longer leaving a blank beside a tall one; the lists
  sorted by completion, name, number of entries or bottles in the cellar (remembered).
- A wine with a vineyard outline opens its map on the vineyard (with its neighbours around it), not the whole
  appellation; a small vineyard is never framed too close.
- Satellite asks for one photo per place: IGN's in France, Esri's elsewhere, both only at a border (it used to load
  Esri's under every one of IGN's).
- **Draw on the map you're looking at**: Draw outline (an appellation's, a vineyard's) and Draw vineyard (from a
  wine) work on the page's own map, made full size where you were, on the photos, the tools over it; the
  lieux-dits' outlines and names to draw along. The separate drawing dialog and new-vineyard page are gone.
- A map opened full size (⤢) keeps its view: the same map, not drawn again.
- Pages open their map full size by default (Settings › Appearance › Maps: *In the page* to keep it in the page).
- **Maps that stay put**: clicking a shape opens its card on the map (name, details, a link to its page), on a
  phone too, instead of going to its page; clicking a legend entry zooms to it and opens its card. The home map's
  regions open their card the same way.
- **Appellations, Vineyards and Lieux-dits** on every map and on the Map page: each filled, outline only or hidden.
- Vineyards in their region's colours, a shade darker than the appellations, with a darker outline (no longer a
  green per village).
- **Lieux-dits** have their own switch, next to Appellations and Vineyards: hiding the vineyards no longer hides them.
- Zoomed in to the lieux-dits, the appellations' and vineyards' fills fade so the lieux-dits read through them (a
  selected Savennières hid its own).

## v0.3.4

- **See a suggested lieu-dit before linking it**: in Maintenance's preview, *map* opens it among its neighbours and
  villages, the wine's appellation outlined.
- On Satellite, the appellations and vineyards are drawn light enough to see the vines under them. The Terrain
  background is gone (Plain and Satellite remain; a default of Terrain becomes Plain).
- **Champagne's lieux-dits**: 9,000 more, in the Marne, the Aube and the Aisne (Les Chétillons, La Côte Faron, Les
  Crayères…). INAO publishes no parcel plan for Champagne: its vines are its appellations' areas where OpenStreetMap
  (and the farmers' RPG declarations) have vineyards.
- A lieu-dit found whatever the plural: a cuvée "Les Chétillons" is the cadastre's "Chétillon"; a search without
  its article ("les chetillons").

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
