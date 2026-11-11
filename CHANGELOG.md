# Changelog

## Unreleased

- **A smaller install**: geopandas (and pandas with it) is no longer needed: the app reads its maps with pyarrow and
  shapely alone. About 380 MB less to install, and a lighter Docker image.
- **Getting started**: a new installation's home page says what to do first (the map outlines, your cellar from a
  file or a first bottle, the help), each step ticked when it's done; it can be put away.
- **The Producers page shows yours first**: those you have wines of, tasted, hold or listed; the whole directory
  (the thousands of producers WineLib ships with) is a click away, and shown on a new installation.
- **Backups hold your photos**: Maintenance › Backup also saves the tasting photos in a zip (when they changed), and
  keeps the last ten backups of each kind (two of the photos'), removing the older ones it wrote. Settings › Your
  data downloads the photos too. The restore script puts them back (`--photos`), uses the app's own database by
  default, and ships in the Docker image. A new page says how to update, back up, restore and move:
  [Updating, backups and moving](https://maxlmn.github.io/winelib/upkeep/). (The help no longer promises a nightly
  price refresh: the app has no schedule of its own.)
- **Tasting Notes in one column**: an occasion's day, place and photo at the side, its wines beside, each note at
  the right of its wine; read down, not across two columns.
- **A tasting history's photos** at a size to see (they had shrunk to a thumbnail), opened whole on a click.
- **New screenshots** in the README and on the website, of the app as it looks now, taken from the demo cellar by a
  script (`app/web/scripts/screenshots.mjs`, then `scripts/screenshots_compose.py`), so they can be retaken.
- **The outline's drawing tools are in a row again** (they had stacked one under the other, the card's width).
- **The version is said where you look for it**: at the bottom of Settings in the app, and on the website (its
  home page and every page's foot), linked to the release.

## v0.6.0

- **Safer updates and access**: the database is copied before an update changes it (SQLite:
  `backups/before-<revision>.sqlite`, and a failed migration says where it is); the app shows its version (About,
  `/api/health`). **If you reach WineLib through a domain of your own** (not an IP address, a local or a Tailscale
  name), list it in `WINELIB_HOSTS`: it now refuses a name it doesn't know, so that a web page elsewhere can't
  reach it through your browser.
- **A wine left without a producer** (by an import of an earlier version) gets *Unknown producer*, so its pages
  open: the vintage page it was on failed. Fix or delete it from there.
- **Names with an accented capital are found** on SQLite (the default install): a grape's page by its name
  ("Muscat Blanc À Petits Grains") said it didn't exist, and so did other look-ups by name. Postgres wasn't affected.
- **A cellar import finds your plain wines**: a row naming the appellation as its cuvée ("Jamet, Côte-Rôtie") is the
  producer's wine without one, the one you have, not a new wine named after its appellation; and a whole name
  (CellarTracker's Wine) has a hyphenated appellation cut off too.
- **A tasting note of a wine you hold** says so ("2 in your cellar") and offers to take one from the cellar; the
  form opens on the cellar or another wine as you last chose. An empty score shows no knob.
- **The app's own questions** (Maintenance's runs, an import, a list or an outline deleted) in its dialog, not the
  browser's; and every field, menu and checkbox in the app's style, the lists' too (they were the browser's own,
  light in dark mode).
- **Deleting a tasting asks whether to put the bottle back** in the cellar (ticked when that tasting took one out;
  tastings logged before this version don't record it). A tasting can't take a bottle from an empty line.
- **Edits keep what they should**: a wine moved to another producer keeps its list entries; deleting a producer
  only removes its own list entries; editing a tasting no longer changes the cellar bottle it came from.
- **Merges keep the duplicate's details**: its grapes and shares, region, vineyard and other filled-in fields; a list
  that held both wines keeps one entry, with both notes. *Duplicate wines* only pairs wines with the same region,
  vineyard and LWIN, and its preview lets you pick the groups to merge.
- **CSV imports**: identical rows add up (importing a file twice still adds nothing); notes-only tastings are all
  kept; a close match arrives unticked, with what it's close to; "12,50" and "93-95" read right; Excel's CSV keeps
  its accents; the preview says how ambiguous dates were read and can switch day and month; line numbers match the
  spreadsheet.
- **Safer**: *Fill from a link* only reads public internet pages; a Backup that misses a table fails; the MCP
  server's writes aren't marked safe to repeat, and ask for a code when the client can't confirm.
- **The Unknown region is plain text**, not a dead link; an empty cellar says so on the home page.
- **Keys in `.secrets.env` are read**: the file next to `run.py` (or one in the data folder) was ignored when the
  app ran outside Docker, though the app and the docs point to it; the environment still wins.
- **The field you're in shows it**: a form's text, number and date fields had no focus mark (nor a refused one its
  red border).
- **A CellarTracker import** no longer names a wine "Unknown" (its word for nothing), takes the vineyard for a wine
  without a designation, and reads its vintage 1001 as non-vintage; the result counts the bottles, not their lines.
- **＋ New wine… keeps what you typed**: "chateau margaux 2015" starts the new wine with its producer and vintage.
- **Faster on a large cellar** (measured with 5,000 wines): the cellar's data in under half the time, the tasting
  form's bottle search and the home page's checks about ten times quicker; the app's own files are kept by the
  browser, not asked again at each page.
- **A slow or absent server says so**: a first screen while the app loads (it was a blank page), a bar at the top
  while a page waits for its data (a click showed nothing), and *Can't reach WineLib* with *Try again* when the
  server doesn't answer (it said "500 Internal Error"). The home page's map and the search say when they failed.
- **A new default look**: the Bordeaux palette and serif headings, where you haven't picked your own (Settings ›
  Appearance has the others, Rosé and the plain headings included).
- **A phone's bar at the bottom**: Home, Cellar, ＋ (a bottle, a tasting, a restaurant visit), Tastings and Search
  within the thumb's reach; the other pages stay behind the menu button.
- **Tasting cards, lighter**: an occasion's place and day on one plain card (no band, no box in a box), each wine
  with its appellation under it and its note in full colour; a wine without a note offers *Add a note*. On the
  Tasting Notes page the cards sit on the page itself.
- **Detail pages, plain rows**: a wine's, bottle's, producer's (and the others') Cellar tab is its bottles as lines,
  each saying how many and where (no card per storage place); the History tab is a row a day, its date and place
  small at the side, the wines and their notes beside (its appellation under the wine, *Add a note* for one
  without).
- **A phone's top bar** keeps the brand, the theme and the menu: search is in the bar at the bottom.
- **The home page's latest tastings and recent purchases** are plain rows too: a tasting's day and place small on
  a line over its wines; a purchase with its price, how many, its day and where it was bought.
- **Easier to read and to reach**: the text on a coloured button follows the palette (dark on a light accent, in
  dark mode too), greys and gold stars darker on white, the paler palettes' links darker; on a phone, fields
  that no longer make iOS zoom and buttons a finger finds; less motion when the system asks for it.
- **By keyboard**: *Skip to the page* first, the current page said to a screen reader; the search keeps Tab in its
  field, names the shortcut as your computer does (Ctrl K, ⌘K) and gives the focus back when it closes; the ⋯ menu
  takes the focus, moves with the arrows and gives it back on Escape.
- **One date format**: a tasting's page title, its other tastings and the tasting list wrote 2026-09-09.
- **The Cellar page's storage cards** sit on the page itself, as the tasting cards do: not cards in a card.

## v0.5.0

- **A website, with a demo**: [maxlmn.github.io/winelib](https://maxlmn.github.io/winelib/) shows what WineLib does,
  how to install it and the guide; its [demo](https://maxlmn.github.io/winelib/demo/) is the app on a sample cellar,
  read-only, maps, lists and search included. Both are rebuilt at each release.
- **The satellite view outside France needs your own Esri key** (`ESRI_API_KEY` in `.secrets.env`, a free ArcGIS
  Location Platform account): Esri's terms don't allow its World Imagery without one, which WineLib used. Without
  a key, Satellite is IGN's photos in France over the plain map, which shows elsewhere. Settings › Integrations
  says how to get one.
- **Fill from photos**: a new bottle from photos of its labels, the front and (optional) the back, taken or picked on
  the bottle form; Claude reads the producer, cuvée, vintage, appellation, colour, size and a sparkling wine's
  disgorgement, and the reading is matched against your cellar as *Fill from text*'s is (the wine you have, a new
  vintage or disgorgement of it, or a new wine). Says what it couldn't read; nothing is saved until you do. Needs your
  own Anthropic API key (`ANTHROPIC_API_KEY` in `.secrets.env`): the photos are sent to Anthropic, shrunk to ~1600 px.
- **A region's map** draws every appellation you've tasted or hold bottles from, and their vineyards: the top list's
  as before, the others fainter. It drew only the top 8 appellations, and no vineyards.
- **Vineyards for your wines** (Settings › Maintenance): cuvées named after a vineyard WineLib has an outline for, in
  their region, linked to it ("Escolle Vineyard", "Wehlener Sonnenuhr Spätlese", "Chaillots"); the site's kind, the
  grape or the village's adjective around the name are allowed. A preview to tick, each on its map; ticked when it's
  the only one and in a village the appellation names. *Lieux-dits for your wines* leaves those cuvées to it.
- **A wine at random**: the home page's dice opens one of your wines, any you hold or have tasted.
- **Lieux-dits for your wines** finds more: a premier or grand cru's lieu-dit by its village appellation (La
  Boudriotte, *Chassagne-Montrachet Premier Cru*), and words saying nothing of the place around it (Fût 3, Franc de
  Pied, Première Trie, Vin Jaune). Less sure, never ticked: a lieu-dit of the producer's village the cadastre puts in
  another appellation (Les Greffieux, Hermitage), or a distinctive one with other words around it (La Peyanne Cuvée
  Lou). A colour in a cuvée's name is the wine's own: a lieu-dit named only with one (Rosé, Les Blanches) is offered
  for a still wine of another colour only, and one named only with wine's words (Vieilles Vignes, La Côte) never.
- **A grape's page**: all it says of the grape in one card, and beside it, half the page each, its family (each parent's
  own parents stacked above it) over its history, cellar and producers; one under the other on a small screen. Its origin is said once, and *Classic regions* gives way to where
  it's planted.
- **Grape descriptions shipped with the app, no more Wikipedia**: a grape's page shows Pl@ntGrape's sheet (origin, its
  wines, ripening, growing, diseases) and where it's planted (the University of Adelaide's hectares to 2023: world
  rank, top countries and regions). Nothing is looked up while you use the app, and the grapes' photos are gone. That
  data has its own licence (CC BY-NC-SA 4.0: not for commercial use, `app/api/data/grapes/LICENSE`), not the code's MIT.

## v0.4.0

- **Find a lieu-dit by name** for a vineyard: a wine's *Add its vineyard* (the ⋯ menu; was *Draw its vineyard*) and a
  vineyard's outline search the cadastre's lieux-dits (village and AOC beside each). One picked is drawn on the map:
  saved as it is, the vineyard is that lieu-dit; reshaped first, it's saved as your own outline, named after it.
- **A sparkling wine's disgorgement** in its title, smaller, after the vintage ("NV Disg. 23", "2012 Disg. 24"; the full
  date in its tooltip): a vintage's was shown nowhere.
- **Change a wine's vineyard** from its ⋯ menu (*Change its vineyard*, when it has one): a lieu-dit picked or a vineyard
  drawn replaces it, on its other vintages that had the same one too.
- **Grand Cru, Premier Cru** capitalised in appellation and vineyard names ("Alsace Grand Cru Brand", "Pommard Premier Cru
  Clos des Epeneaux"; INAO writes them in lower case): the reference lists a new installation starts from, and the
  map's lieux-dits. An existing database keeps its names.
- **On a phone, the map full size**: the page's cards float over its lower half, the map behind them (no more sheet);
  a touch there scrolls the cards, one above pans the map.
- Fix: a lieu-dit picked for a vineyard, or an outline imported, wasn't drawn (nor could be saved) when the app is
  opened over plain http, as on a NAS: only https and localhost have the browser's `crypto.randomUUID`.
- Fix: a check opened from *Needs attention* started its Maintenance preview over and over; once now.
- **Duplicate wines' preview, readable**: each copy on its own line, linked to its page, with what it holds (bottles
  and where, tastings, scores, LWIN, vineyard) and whether it's kept or merged into the other.
- **Settings opens at once**: *Needs attention* fills in when its checks are done (they took ~3 s on a NAS).
- *Needs attention* checks again each time its tab opens: a task you just ran no longer leaves its warning up.
- Market prices: a bottle whose price is over 6 months old and that WineLabs no longer prices loses that price (marked
  *no price*, asked again a month later) instead of staying in *Needs attention* and being asked every night.

## v0.3.8

- **A wine's header, shorter**: its grapes (after a grape icon), blend and drinking window just under the appellation;
  no LWIN, no disgorgement (the title's vintage says it: "NV - Oct 2024"), no empty space when there's nothing more.
- **A drinking window from the ⋯ menu**: *Add a drinking window* (or *Edit*) asks for its years under the appellation
  (either left open, or cleared).
- The menu's *Add to your wishlist* is gone: *Add to a list* picks the wishlist too.
- **Champagne's crus**: its 17 grand cru and 42 premier cru villages (the échelle des crus) can be drawn as vineyards,
  each its village's Champagne vines, shaded on the map like Burgundy's crus; *Champagne Grand Cru* and *Champagne
  Premier Cru* as appellations, their villages together (the map pack's `champagne_cru` and `champagne_mention`).

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
- **A wine's page, said once**: the facts list is gone (the header already names the producer, colour, region and
  appellation, the map its vineyard); the grapes, blend, disgorgement, drinking window and LWIN on one line under the
  title. One button, ＋ Tasting, and a ⋯ menu for the rest (a bottle, a critic's score, a plug-in's Fetch from Robert
  Parker, a list, the wishlist, Edit, Draw its vineyard); no Critics card without a score, no Lists card when it's on
  none (the menu adds them); the Vintages card just its pills. A producer's page: ＋ Wine, and its ⋯ menu.
- **The other pages, tidied the same way**: every detail page's actions are a ⋯ menu at its card's top right and its
  main action under it, a small icon named on hover; the add buttons (tasting, purchase, visit, place, producer, list)
  are icons; an appellation's, a vineyard's and a place's facts no longer repeat their header. A bottle's date, vendor
  and provenance sit small under its price; a tasting's page says the wine and the bottle in two lines under its
  header (no Wine and Bottle cards), the critics once in its note, That session only with other wines.
- No stats boxes repeating the tabs (Bottles in cellar, Wines tasted, Wines): the Cellar tab says the cellar's value
  ("Cellar 12 · €3,400"). A wine's and a bottle's cellar cards are plain (no rack strip, no reds / whites split); a
  bottle's "What happened to it" only for the bottles that left other than drunk (gifted, sold, broken).
- **A bottle's page**: the bottle is a band at the foot of its wine's card, two lines: how many and where (its ⋯
  menu and the glass beside them), what it cost and what it's worth; the shelf strip only when its storage holds
  several bins. The Cellar tab marks the bottle's own line.
- **Map legends in columns**: one row of controls (the layers, the basemap, the full-size button as an icon), every
  appellation and vineyard in columns, a long name cut and whole on hover.
- **A producer's page**: its map takes the card's width, the legend carrying the producer's tastings and bottles by
  appellation and vineyard (no Top appellations nor vineyards list beside it; the list comes back when the map has
  nothing to draw). The lists it's on sit in its header card.
- **A wine's lists** sit in its header card too, only those naming this vintage, another vintage or the cuvée: a
  producer's lists stay on the producer's page (`/api/lists-of`).
- **A wine's style**: small tags under its appellation, nothing when there are none; the ⋯ menu's *Add its style*
  opens the picker there.
- **Settings in three tabs**: Settings, Maintenance, and **Needs attention**: what the quick checks find (wines entered twice, records pointing at nothing,
  a vintage under two appellations, market prices no longer refreshed, cellar wines
  without an LWIN, restaurants without coordinates), its count on the tab, each opening its Maintenance task with
  the preview run.
- **Keeping vintages together** (Settings › Maintenance): *Cuvées under several appellations* finds a vintage entered twice or left under an old name.
- Market prices: a wine WineLabs has no price for is marked so on its bottles and asked again a month later, not every
  night.
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
