"""CSV backup of every table, shared by winelib_maintenance.py --backup-csv and the app's Maintenance › Backup."""
import csv
import os
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
