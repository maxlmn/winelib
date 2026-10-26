## How it was built

The reference data started as one cellar's database, completed from the official sources above (October 2026):

- **Regions**: one level of wine regions in every main country (Italy's 20 regions, Spain's classic wine zones,
  Germany's 13 Anbaugebiete, Portugal's wine regions, Austria's states, Australia's states, the US states with the
  most AVAs), each appellation filed under the region that holds its outline. A national appellation (Vin de France,
  Vino d'Italia, Deutscher Wein...) is filed under its country, and its wines keep their own region.
- **Appellations**: every name INAO delimits, every AVA in force, every wine PDO and PGI in the EU register, and
  eight other countries' official registers, each one's details starting with what it is (AOP, DOCG, AVA,
  complementary geographic name...).
- **Grapes**: the notable varieties, named as wine people name them, with their common synonyms only (VIVC lists
  hundreds that would match the wrong grape); each one's berry colour, origin and parents from VIVC, whose
  DNA-confirmed parents are preferred to any other.
- **A wine's grapes**: a list (the first the main grape, shares optional) and a blend style (Bordeaux, Rhône,
  Champagne, Field or Other blend).

New installations get it all; an update fills what's empty and never moves your rows. The full record, every
decision and how to refresh it, is in the repository: `docs/reference-data.md`.
