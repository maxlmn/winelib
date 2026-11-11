"""The app's Maintenance › Backup: every table to CSV, the tasting photos to a zip when they changed, and the older
backups pruned."""
import csv
import os
import re
import shutil
import zipfile
from datetime import datetime

from sqlalchemy import inspect, text


class BackupIncomplete(RuntimeError):
    """Some tables couldn't be saved: the backup isn't whole (the others are in `folder`)."""

    def __init__(self, failed, folder):
        self.failed, self.folder = failed, folder
        super().__init__(f"Backup incomplete: {', '.join(failed)} couldn't be saved")


def backup_csv(engine, backup_root, log=print):
    """Each table (all of them but Alembic's, so a new one is never left out) to CSV in a new timestamped folder of
    backup_root. Returns the folder; raises BackupIncomplete (after saving the others) when a table fails."""
    backup_dir = os.path.join(backup_root, datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
    os.makedirs(backup_dir, exist_ok=True)
    failed = []
    tables = sorted(t for t in inspect(engine).get_table_names() if t != "alembic_version")
    with engine.connect() as conn:
        for table in tables:
            try:
                result = conn.execute(text(f'SELECT * FROM "{table}"'))
                rows = result.fetchall()
                with open(os.path.join(backup_dir, f"{table}.csv"), "w", encoding="utf-8", newline="") as f:
                    w = csv.writer(f)
                    w.writerow(result.keys())
                    w.writerows(rows)
                log(f"✅ {table}: {len(rows)} rows")
            except Exception as e:
                log(f"❌ {table}: {e}")
                failed.append(table)
    if failed:
        log(f"❌ CSV backup incomplete ({len(failed)} of {len(tables)} tables failed); the rest is in {backup_dir}")
        raise BackupIncomplete(failed, backup_dir)
    log(f"CSV backup saved in {backup_dir}")
    return backup_dir


def _photos(photos_dir):
    """The photo files (not folders, not hidden files), sorted."""
    if not os.path.isdir(photos_dir):
        return []
    return sorted(f for f in os.listdir(photos_dir) if not f.startswith(".") and os.path.isfile(os.path.join(photos_dir, f)))


def backup_photos(photos_dir, backup_root, log=print):
    """The tasting photos in one zip of backup_root (photos_<time>.zip), when there are any and the last such zip
    doesn't already hold them all as they are (their names and sizes). Its path, or None when nothing was written.
    Stored, not compressed: photos don't shrink."""
    names = _photos(photos_dir)
    if not names:
        return None
    now = {n: os.path.getsize(os.path.join(photos_dir, n)) for n in names}
    last = max((f for f in os.listdir(backup_root) if PHOTOS.fullmatch(f)), default=None) if os.path.isdir(backup_root) else None
    if last:
        try:
            with zipfile.ZipFile(os.path.join(backup_root, last)) as z:
                if {i.filename: i.file_size for i in z.infolist()} == now:
                    log(f"Photos unchanged since {last}: not copied again")
                    return None
        except (OSError, zipfile.BadZipFile):
            pass  # an unreadable zip: a new one
    os.makedirs(backup_root, exist_ok=True)
    target = os.path.join(backup_root, f"photos_{datetime.now():%Y-%m-%d_%H%M%S}.zip")
    with zipfile.ZipFile(target + ".part", "w", zipfile.ZIP_STORED) as z:
        for n in names:
            z.write(os.path.join(photos_dir, n), arcname=n)
    os.replace(target + ".part", target)
    log(f"✅ {len(names)} photos saved in {target}")
    return target


# The backups this app writes, by what they are: the CSV folders, the SQLite copies, the photo zips, the copies made
# before a migration. Nothing else in the folder is ever touched (a .sql dump is yours)
CSV_FOLDER = re.compile(r"\d{4}-\d\d-\d\d_\d\d-\d\d-\d\d")
SQLITE_COPY = re.compile(r"winelib_\d{4}-\d\d-\d\d_\d{4}\.sqlite")
PHOTOS = re.compile(r"photos_\d{4}-\d\d-\d\d_\d{6}\.zip")
BEFORE = re.compile(r"before-\w+\.sqlite")
KEEP = [(CSV_FOLDER, 10), (SQLITE_COPY, 10), (PHOTOS, 2), (BEFORE, 5)]


def prune(backup_root, keep=KEEP, log=print):
    """Removes the older backups of each kind beyond those to keep (the newest by name: their names are their
    times; the copies before a migration by their file's time). The names removed."""
    if not os.path.isdir(backup_root):
        return []
    removed = []
    for pattern, n in keep:
        found = [f for f in os.listdir(backup_root) if pattern.fullmatch(f)]
        key = (lambda f: os.path.getmtime(os.path.join(backup_root, f))) if pattern is BEFORE else None
        for name in sorted(found, key=key, reverse=True)[n:]:
            path = os.path.join(backup_root, name)
            try:
                shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)
                removed.append(name)
            except OSError as e:
                log(f"Couldn't remove the old backup {name}: {e}")
    if removed:
        log(f"Older backups removed ({len(removed)}): the last ones of each kind are kept")
    return removed
