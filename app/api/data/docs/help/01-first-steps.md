# First steps

Setting WineLib up and getting your wines in.

## The setup page

The first start opens on a short setup page; everything on it can be changed later in Settings.

- **Main currency**: totals and values are shown in it; a bottle bought in another currency is converted (the
  exchange rates are in Settings › Currencies).
- **Where you keep bottles**: a *storage group* per place, each with a prefix and how many bottles a bin holds.
  A group "Home" with prefix `H` and 10 per bin gathers the locations `H1`, `H2`... and the shelf map shows how full
  each bin is. Every other location goes in one more group (Cellar, unless you rename it).
- **Preferred critic**: lists sort by this critic's score; without one, the first critic you add scores for.

## The map's outlines

The appellations' outlines aren't in the download: Settings › Maintenance › **Map outlines** fetches them (France,
the EU, the US, Australia and Burgundy's premiers crus) and links them to the appellations.

## Your wines

- From another app or a spreadsheet: Settings › Maintenance › **Import a cellar** (see *Bringing your wines in*).
- One by one: **+ Add purchase** on the Home page for bottles you bought, **+ Add tasting** for a wine you drank
  (also in ⌘K, and on a wine's page: **+ Bottle**, **+ Tasting**). A wine is a producer, a cuvée,
  a vintage, its type, appellation and grapes; the producer, appellation and grapes come from lists as you type
  (a new one is created when it isn't there).

## Finding your way

**⌘K** (Ctrl K) searches everything: producers, wines, appellations, grapes, places. Every name is a link: a wine to
its producer, appellation, vineyard, grapes and vintage, and back.

## On your phone

WineLib installs like an app, with its own icon, full screen: open it in the phone's browser, then **Share › Add to
Home Screen** (iPhone, Safari) or **Install app** (Android, Chrome; on a computer, the install button in the address
bar). The app keeps its own files on the phone, so it opens at once; your data stays on your server, so the phone
needs to reach it: at home on the same Wi-Fi, elsewhere through Tailscale or your own sign-in in front. Installing
needs an https address (Tailscale gives one: `tailscale serve`), or the computer itself (`localhost`).
