"""The Host check (hosts.py), the copy before a migration (migrate.copy_before), the version (/api/health)."""
import os
import sqlite3

from sqlalchemy import create_engine

import hosts
import migrate
import paths
from version import VERSION


def seed(session):
    pass


def test_home_names_are_answered():
    for host in ("192.168.1.2:8000", "127.0.0.1", "[::1]:8000", "localhost:8000", "nas", "jupiter:8000", "wine.local",
                 "jupiter.tail1234.ts.net", "cave.home.arpa", "testserver"):
        assert hosts.allowed(host, []), host


def test_other_names_are_refused_unless_listed():
    for host in ("attacker-rebind.example:8000", "wine.example.com", "", "evil.com."):
        assert not hosts.allowed(host, []), host
    assert hosts.allowed("wine.example.com", ["wine.example.com"])
    assert hosts.allowed("a.example.com:443", ["*.example.com"]) and not hosts.allowed("example.org", ["*.example.com"])
    assert hosts.allowed("anything.at.all", ["*"])


def test_a_foreign_host_gets_a_403_that_says_what_to_do(client):
    r = client.get("/api/export.json", headers={"host": "attacker-rebind.example:8000"})
    assert r.status_code == 403 and "WINELIB_HOSTS" in r.text
    assert client.get("/api/health", headers={"host": "192.168.1.2:8000"}).status_code == 200


def test_health_says_the_version(client):
    assert client.get("/api/health").json() == {"ok": True, "version": VERSION}


def test_the_database_is_copied_before_a_migration(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "BACKUP_DIR", str(tmp_path / "backups"))
    file = tmp_path / "winelib.db"
    engine = create_engine(f"sqlite:///{file}")
    assert migrate.copy_before(engine) is None  # no database yet
    migrate.upgrade(engine)  # a new one, at the latest revision
    assert migrate.copy_before(engine) is None and not os.path.exists(tmp_path / "backups")  # nothing to migrate
    with engine.begin() as conn:  # as an older version left it
        conn.exec_driver_sql("UPDATE alembic_version SET version_num = '0009'")
        conn.exec_driver_sql("INSERT INTO producers (name) VALUES ('Clos Rougeard')")
    copy = migrate.copy_before(engine)
    assert copy == str(tmp_path / "backups" / "before-0009.sqlite")
    with sqlite3.connect(copy) as c:
        assert c.execute("SELECT name FROM producers").fetchall() == [("Clos Rougeard",)]
        assert c.execute("SELECT version_num FROM alembic_version").fetchone() == ("0009",)
    engine.dispose()
