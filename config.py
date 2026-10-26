"""The scripts' settings: the database (DB_URL), from the environment or .secrets.env next to this file."""
import os


def _load_secrets(path=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".secrets.env")):
    """KEY=value lines (see .secrets.env.example); variables already set win."""
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    except OSError:
        pass


_load_secrets()

# DB_URL when set (Postgres: postgresql://user:password@host/db), else the app's own SQLite file in data/
DB_URL = os.getenv("DB_URL") or f"sqlite:///{os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'winelib.db')}"
BACKUP_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups")
