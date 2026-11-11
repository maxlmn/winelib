---
title: Updating, backups and moving
description: Update WineLib, back up and restore your data, move it to another machine or to Postgres, and reach it from other devices.
---

Your data lives apart from the program: the database, the tasting photos, the map outlines, the backups and the
plug-ins are in one data folder (the `/data` volume in Docker; your user folder for the release, `data/` in a
checkout). Updating replaces the program only.

## Updating

- **Docker**: `docker compose pull && docker compose up -d`.
- **Python**: unzip the new release over the old one (or in a new folder), then `python run.py`.

At its first start the new version brings the database up to date by itself. With the built-in SQLite database it
copies it first, to `backups/before-<revision>.sqlite`; if the update fails, the log says where the copy is. Going
back to an older version isn't supported: restore a backup made with it.

**About** (and the bottom of Settings) says which version you run;
[the changelog](https://github.com/maxlmn/winelib/blob/main/CHANGELOG.md) says what changed.

## Backing up

**Settings › Maintenance › Backup** saves, in the data folder's `backups/`:

- every table as CSV, in a folder named after the time;
- with SQLite, a copy of the database (`winelib_<time>.sqlite`);
- your tasting photos in a zip (`photos_<time>.zip`), when they changed since the last one.

It keeps the last ten of each (two of the photos' zips) and removes the older ones; it never touches a file it
didn't write. Each backup can be downloaded from the same page.

The backups are in the same place as the data: copy them elsewhere now and then (another disk, your NAS's own
backup), or download them. With **Postgres**, dump the database with its own tool (`pg_dump`); a `.sql` file put
in `backups/` is listed with the others.

**Settings › Your data** downloads everything at once, to keep or take elsewhere: the whole database as JSON (or
CSV), and the photos as a zip.

To back up on a schedule, call the task from your system's scheduler (cron, the NAS's task scheduler):

```sh
curl -X POST http://127.0.0.1:8000/api/maintenance/backup -H 'content-type: application/json' -d '{"commit": true}'
```

## Restoring, or moving to another machine

1. On the old installation: **Settings › Your data › Download as JSON**, and **Download the photos**.
2. Install WineLib on the new machine (don't add anything yet).
3. Rebuild the database from the export, with the photos:

   ```sh
   # Python
   python scripts/restore_export.py winelib_export_2026-10-25.json --photos winelib_photos_2026-10-25.zip

   # Docker: copy the files in, then run the script in the container
   docker compose cp winelib_export_2026-10-25.json winelib:/data/
   docker compose cp winelib_photos_2026-10-25.zip winelib:/data/
   docker compose exec winelib python /app/scripts/restore_export.py /data/winelib_export_2026-10-25.json --photos /data/winelib_photos_2026-10-25.zip
   ```

4. Restart WineLib, then download the map outlines again (Settings › Maintenance › Map outlines).

The script only fills a new or empty database: it refuses one that already has your wines.

With SQLite you can also put a copy back by hand: stop WineLib, replace `winelib.db` in the data folder with a
`winelib_<time>.sqlite` (or `before-<revision>.sqlite`) from `backups/`, and start it again.

## Moving to Postgres (or back)

The same export and script, pointed at the other database:

```sh
python scripts/restore_export.py winelib_export_2026-10-25.json --to postgresql://user:password@host/winelib
```

Then set `DB_URL` to that address (`.secrets.env`, or `environment:` in `docker-compose.yml`) and restart.

## Reaching it from other devices

WineLib has no accounts or passwords: whoever can reach it can read and change everything. Out of the box it
answers on its own computer only.

- **On a home server or a NAS**, to reach it from the other devices of your home network, change the port line of
  `docker-compose.yml` from `"127.0.0.1:8000:8000"` to `"8000:8000"` (with Python: `python run.py --host 0.0.0.0`),
  then open `http://<the machine's address>:8000`. Only do this on a network you trust.
- **From outside your home**, use a private network between your devices such as [Tailscale](https://tailscale.com),
  or a reverse proxy with its own login. Never expose it to the internet as it is.
- WineLib answers to an IP address, a local name (`nas`, `wine.local`) or a Tailscale name. Reached through a domain
  of your own, list it in `WINELIB_HOSTS` (`.secrets.env`, or `environment:`): otherwise it answers 403.
- *Add to Home Screen* on a phone installs it with its own icon; that needs HTTPS (Tailscale's `tailscale serve`
  gives it), not a plain `http://` address.
