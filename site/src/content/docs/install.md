---
title: Install
description: Run WineLib on your computer or home server, with Docker or Python.
---

WineLib runs on your own machine: a computer, a home server or a NAS. Pick Docker or Python; both keep your data
apart from the program, so updating never touches it.

## With Docker

Save [`docker-compose.yml`](https://github.com/maxlmn/winelib/blob/main/docker-compose.yml) in a folder, then:

```bash
docker compose up -d
```

Open http://localhost:8000. Your data lives in the `winelib-data` volume: the database, photos, map outlines and
backups. The image is published for both Intel and ARM machines (`ghcr.io/maxlmn/winelib`), so it runs on most NAS
boxes and a Raspberry Pi too.

To update:

```bash
docker compose pull && docker compose up -d
```

## With Python

You need Python 3.11 or newer. Download the zip of the
[latest release](https://github.com/maxlmn/winelib/releases/latest), unzip it, then from that folder:

```bash
pip install -r app/api/requirements.txt
python run.py
```

It opens http://127.0.0.1:8000 in your browser. Your data lives in your user folder:

| System | Folder |
|---|---|
| Windows | `%APPDATA%\winelib` |
| macOS | `~/Library/Application Support/winelib` |
| Linux | `~/.local/share/winelib` |

`python run.py --data <folder>` keeps it somewhere else. To update, unzip the newer release anywhere and run it: it
finds your data where it was.

## The first start

WineLib opens on a short setup page: your main currency, where you keep bottles, your preferred critic. All of it
can be changed later in Settings. Then, in **Settings › Maintenance**:

- **Map outlines** downloads the appellations', vineyards' and lieux-dits' outlines (the map pack, a few hundred
  MB);
- **Import a cellar** brings in your CellarTracker or Vivino export, or your own spreadsheet.

[First steps](../guide/first-steps/) goes through it all.

## Reaching it from your phone

WineLib has no accounts or passwords: it listens on your computer only. To use it from your phone or another
machine, put your own sign-in in front of it, for instance [Tailscale](https://tailscale.com) (a private network
between your devices) or a reverse proxy with a login. Never expose it to the internet as it is.

On the phone, *Add to Home Screen* installs it with its own icon.

## Your data

- **Back up**: Settings › Maintenance › Backup copies the database; Settings › Your data exports everything as JSON
  or CSV.
- **Postgres** works too, instead of the built-in SQLite file: set `DB_URL`
  (`postgresql://user:password@host/winelib`).
- **Optional services** (market prices, labels read from photos, satellite photos outside France) need keys of your
  own: see [Integrations](../integrations/).

## From the source

You need Node.js to build the web app once:

```bash
git clone https://github.com/maxlmn/winelib && cd winelib
cd app/web && npm install && npm run build && cd ../..
pip install -r app/api/requirements.txt
python run.py
```

Or `docker compose up -d --build` from the checkout.
