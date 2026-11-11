"""The Backup task's photos and pruning (tasks/backup.py), the photos' download, the restore script's photos."""
import io
import os
import sys
import zipfile

import paths
from tasks import backup


def seed(session):
    pass


def photos(folder, **files):
    os.makedirs(folder, exist_ok=True)
    for name, content in files.items():
        with open(os.path.join(folder, name), "wb") as f:
            f.write(content)


def test_photos_are_zipped_once_until_they_change(tmp_path):
    src, root = str(tmp_path / "images"), str(tmp_path / "backups")
    assert backup.backup_photos(src, root, log=lambda m: None) is None  # no photos: no zip
    photos(src, **{"Chez Paul_2025-01-02.jpg": b"one", "Home_2025-02-03.jpg": b"two!"})
    first = backup.backup_photos(src, root, log=lambda m: None)
    with zipfile.ZipFile(first) as z:
        assert sorted(z.namelist()) == ["Chez Paul_2025-01-02.jpg", "Home_2025-02-03.jpg"] and z.read("Home_2025-02-03.jpg") == b"two!"
    assert backup.backup_photos(src, root, log=lambda m: None) is None  # the same photos: not copied again
    photos(src, **{"Home_2025-02-03.jpg": b"another"})  # one replaced
    again = backup.backup_photos(src, root, log=lambda m: None)  # (the same second: the same name, written anew)
    with zipfile.ZipFile(again) as z:
        assert z.read("Home_2025-02-03.jpg") == b"another"


def test_prune_keeps_the_last_of_each_kind_and_what_isnt_its_own(tmp_path):
    root = str(tmp_path)
    for i in range(1, 13):
        os.makedirs(os.path.join(root, f"2026-01-{i:02d}_10-00-00"))
        open(os.path.join(root, f"winelib_2026-01-{i:02d}_1000.sqlite"), "w").close()
    for i in range(1, 5):
        open(os.path.join(root, f"photos_2026-01-{i:02d}_100000.zip"), "w").close()
    for other in ("winelib_2026-01-01_0900.sql", "notes.txt", "before-0009.sqlite"):
        open(os.path.join(root, other), "w").close()
    removed = backup.prune(root, log=lambda m: None)
    left = set(os.listdir(root))
    assert sorted(removed) == ["2026-01-01_10-00-00", "2026-01-02_10-00-00", "photos_2026-01-01_100000.zip",
                               "photos_2026-01-02_100000.zip", "winelib_2026-01-01_1000.sqlite", "winelib_2026-01-02_1000.sqlite"]
    assert {"winelib_2026-01-01_0900.sql", "notes.txt", "before-0009.sqlite", "2026-01-12_10-00-00",
            "photos_2026-01-04_100000.zip"} <= left


def test_the_backup_task_saves_the_photos_and_lists_them(client, tmp_path, monkeypatch):
    from conftest import wait_job
    from routers import maintenance
    monkeypatch.setattr(paths, "PHOTOS_DIR", str(tmp_path / "images"))
    monkeypatch.setattr(maintenance, "BACKUP_DIR", str(tmp_path / "backups"))
    photos(str(tmp_path / "images"), **{"Home_2025-02-03.jpg": b"jpeg"})
    assert client.post("/api/maintenance/backup", json={"commit": True}).status_code == 202
    job = wait_job(client)
    assert job["status"] == "done" and "photos_" in job["result"]["summary"], job
    listed = [b for b in client.get("/api/maintenance/backups").json() if b["kind"] == "photos"]
    assert len(listed) == 1
    z = zipfile.ZipFile(io.BytesIO(client.get(f"/api/maintenance/backups/{listed[0]['name']}").content))
    assert z.read("Home_2025-02-03.jpg") == b"jpeg"


def test_the_photos_download(client, tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "PHOTOS_DIR", str(tmp_path / "images"))
    assert client.get("/api/export/photos.zip").status_code == 404  # none yet
    photos(str(tmp_path / "images"), **{"Home_2025-02-03.jpg": b"jpeg", ".hidden": b"x"})
    r = client.get("/api/export/photos.zip")
    assert r.status_code == 200 and r.headers["content-disposition"].startswith('attachment; filename="winelib_photos_')
    assert zipfile.ZipFile(io.BytesIO(r.content)).namelist() == ["Home_2025-02-03.jpg"]


def test_restore_puts_the_photos_back_flat(tmp_path):
    sys.path.insert(0, os.path.join(os.path.dirname(paths.ROOT_DIR + os.sep), "scripts"))
    import restore_export
    archive = tmp_path / "photos.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("Home_2025-02-03.jpg", b"new")
        z.writestr("Chez Paul_2025-01-02.jpg", b"kept?")
        z.writestr("../outside.jpg", b"no")
        z.writestr("sub/inside.jpg", b"no")
    target = tmp_path / "images"
    photos(str(target), **{"Chez Paul_2025-01-02.jpg": b"already there"})
    assert restore_export.restore_photos(str(archive), str(target)) == 1
    assert sorted(os.listdir(target)) == ["Chez Paul_2025-01-02.jpg", "Home_2025-02-03.jpg"]
    assert (target / "Chez Paul_2025-01-02.jpg").read_bytes() == b"already there" and not (tmp_path / "outside.jpg").exists()
