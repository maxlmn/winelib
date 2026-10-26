# Bringing your wines in, and out

Your wines from another app or a spreadsheet, critics' scores from a file, and everything out again.

## Import a cellar

Settings › Maintenance › **Import a cellar** reads a CSV: CellarTracker's or Vivino's export, or your own
spreadsheet (one row per wine, with its bottles when it has a quantity or a location, and a tasting when it has a
tasting date, a rating or a note).

1. Pick the file. The columns are recognised by their header (producer, cuvée, vintage, colour, grape, appellation,
   region, quantity, location, size, price, purchase date, tasting date, rating, note...); pick the others by hand.
2. The preview lists every row by producer: a new wine, one of yours, bottles, a tasting. Tick what to add.
3. Run: producers and grapes you don't have are created; nothing already there is added twice, so the same file can
   be imported again.

A grape column holding a style ("Red Bordeaux Blend") becomes the wine's blend; a list ("Grenache 80%, Syrah 20%")
its grapes. Ratings out of 5 or 20 become out of 100.

## Import critic scores

**Import critic scores** reads one critic's reviews (an export, your notes): producer, cuvée, vintage, score, note,
link, date. Name the critic, preview, tick: scores go to the wines you have, the others are added as new wines.

## Taking everything with you

Settings › **Your data** downloads the whole database: one JSON file, or a zip of CSVs. Nothing is locked in.
