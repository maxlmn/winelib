"""Occasion photos: upload, replace, remove, validation, where they show up, and resized copies."""
import io
import os
from datetime import date

import pytest
from PIL import Image

import photos
from db import Bottle, Place, Producer, Region, TastingNote, Wine

DAY = "2024-03-01"
JPEG, PNG = b"\xff\xd8\xff fake jpeg", b"\x89PNG fake png"
IMMUTABLE = "public, max-age=31536000, immutable"


def seed(s):
    wine = Wine(producer=Producer(name="Clos Rougeard"), cuvee="Le Bourg", vintage="2016", region_obj=Region(name="Loire"))
    odette = Place(name="Odette", city="Singapore")
    s.add(TastingNote(bottle=Bottle(wine=wine, qty=0, location="Consumed"), place=odette, location="Odette",
                      date=date(2024, 3, 1)))


@pytest.fixture(autouse=True)
def photo_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(photos, "PHOTOS_DIR", str(tmp_path / "images"))
    monkeypatch.setattr(photos, "THUMBS_DIR", str(tmp_path / "thumbs"))
    return tmp_path / "images"


@pytest.fixture
def thumbs_dir(tmp_path):
    return tmp_path / "thumbs"


def put(client, data, content_type="image/jpeg", place="Odette"):
    return client.put("/api/photos", params={"place": place, "date": DAY}, content=data, headers={"content-type": content_type})


def url(client, place="Odette"):
    return client.get("/api/photos", params={"place": place, "date": DAY}).json()["url"]


def image(w, h, fmt="JPEG", color="red", orientation=None):
    """A real image file; `orientation` sets the EXIF tag phones write instead of rotating the pixels."""
    buf = io.BytesIO()
    exif = Image.Exif()
    if orientation:
        exif[0x0112] = orientation
    Image.new("RGB", (w, h), color).save(buf, fmt, exif=exif)
    return buf.getvalue()


def fetch(client, src, size):
    res = client.get(f"{src}&size={size}")
    assert res.status_code == 200
    return Image.open(io.BytesIO(res.content))


def test_upload_replace_and_remove(client, photo_dir):
    assert client.get("/api/photos", params={"place": "Odette", "date": DAY}).json() == {"url": None}

    assert put(client, JPEG).json()["url"].startswith(f"/api/tastings/photos/Odette_{DAY}.jpg?v=")
    assert (photo_dir / f"Odette_{DAY}.jpg").read_bytes() == JPEG
    assert client.get(f"/api/tastings/photos/Odette_{DAY}.jpg").content == JPEG

    # A new photo in another format replaces the old one, matched case-insensitively
    put(client, PNG, "image/png", place="ODETTE")
    assert sorted(p.name for p in photo_dir.iterdir()) == [f"ODETTE_{DAY}.png"]
    assert f"ODETTE_{DAY}.png?v=" in url(client, "odette")

    assert client.delete("/api/photos", params={"place": "Odette", "date": DAY}).json() == {"deleted": True}
    assert list(photo_dir.iterdir()) == []
    assert client.delete("/api/photos", params={"place": "Odette", "date": DAY}).json() == {"deleted": False}


def test_validation(client, photo_dir, monkeypatch):
    assert put(client, b"<svg onload=alert(1)>", "image/svg+xml").status_code == 415
    assert put(client, b"text", "text/plain").status_code == 415
    assert put(client, b"").status_code == 422
    assert put(client, JPEG, place="  ").status_code == 422
    monkeypatch.setattr(photos, "MAX_UPLOAD", 4)
    assert put(client, JPEG).status_code == 413
    assert not photo_dir.exists() or not any(photo_dir.iterdir())


def test_place_names_cannot_escape_the_folder(client, photo_dir):
    put(client, JPEG, place="../../etc/Le Clos")
    assert [p.name for p in photo_dir.iterdir()] == [f"..-..-etc-Le Clos_{DAY}.jpg"]


def test_photos_show_on_tastings_and_detail_pages(client, photo_dir):
    src = put(client, JPEG).json()["url"]
    assert src == f"/api/tastings/photos/Odette_{DAY}.jpg?v={(photo_dir / f'Odette_{DAY}.jpg').stat().st_mtime_ns // 1_000_000}"
    journal = client.get("/api/tastings").json()
    assert journal["photos"] == {f"odette_{DAY}": src}
    tasting = journal["tastings"][0]
    assert client.get(f"/api/tastings/{tasting['id']}").json()["photo"] == src
    assert client.get(f"/api/wines/{tasting['wine_id']}").json()["tastings"][0]["photo"] == src
    assert client.get(f"/api/places/{tasting['place_id']}").json()["tastings"][0]["photo"] == src


def test_thumbnails_are_resized_and_cached(client, thumbs_dir, monkeypatch):
    src = put(client, image(4000, 3000)).json()["url"]
    for size, box in (("thumb", 480), ("large", 1600)):
        res = client.get(f"{src}&size={size}")
        assert res.headers["content-type"] == "image/jpeg"
        assert res.headers["cache-control"] == IMMUTABLE
        assert Image.open(io.BytesIO(res.content)).size == (box, box * 3 // 4)
    assert len(list(thumbs_dir.iterdir())) == 2

    # Later requests come from the cache: nothing is decoded or encoded again (else the original would be served)
    def boom(*args, **kwargs):
        raise AssertionError("re-encoded")
    with monkeypatch.context() as m:
        m.setattr(Image, "open", boom)
        res = client.get(f"{src}&size=thumb")
    assert res.status_code == 200 and Image.open(io.BytesIO(res.content)).size == (480, 360)

    # Small images are never enlarged; PNGs become JPEGs too; unknown sizes are refused
    put(client, image(300, 200, "PNG"), "image/png")
    small = fetch(client, url(client), "large")
    assert (small.format, small.size) == ("JPEG", (300, 200))
    assert client.get(f"{url(client)}&size=huge").status_code == 422


def test_exif_orientation_is_applied(client):
    put(client, image(800, 600, orientation=6))  # landscape pixels, tagged "rotate 90°": a portrait photo
    assert fetch(client, url(client), "thumb").size == (360, 480)


def test_replaced_photo_gets_fresh_thumbnails(client, photo_dir, thumbs_dir):
    put(client, image(1000, 1000, color="red"))
    first = url(client)
    assert fetch(client, first, "thumb").getpixel((10, 10))[0] > 200
    os.utime(photo_dir / f"Odette_{DAY}.jpg", ns=(10**18, 10**18))  # the replacement's mtime surely differs

    put(client, image(1000, 1000, color="blue"))
    assert list(thumbs_dir.iterdir()) == []  # the old copies went with the old photo
    second = url(client)
    assert second != first
    assert fetch(client, second, "thumb").getpixel((10, 10))[2] > 200

    # Also when the file is changed behind the API's back (copied in by hand): new size, new key
    (photo_dir / f"Odette_{DAY}.jpg").write_bytes(image(1000, 900, color="lime"))
    assert fetch(client, second, "thumb").size == (480, 432)

    client.delete("/api/photos", params={"place": "Odette", "date": DAY})
    assert list(thumbs_dir.iterdir()) == []


def test_unreadable_images_fall_back_to_the_original(client, photo_dir):
    put(client, JPEG)  # not really a JPEG
    res = client.get(f"{url(client)}&size=thumb")
    assert (res.status_code, res.content, res.headers["cache-control"]) == (200, JPEG, IMMUTABLE)
    (photo_dir / "Logo_2024-01-01.svg").write_text("<svg/>")
    assert client.get("/api/tastings/photos/Logo_2024-01-01.svg", params={"size": "thumb"}).text == "<svg/>"


def test_paths_outside_the_folder_are_refused(client, tmp_path):
    put(client, image(100, 100))
    (tmp_path / "secret.jpg").write_bytes(image(100, 100))
    for name in ("..%2Fsecret.jpg", "%2E%2E%2Fsecret.jpg", "..%5Csecret.jpg", f"Odette_{DAY}.txt"):
        assert client.get(f"/api/tastings/photos/{name}", params={"size": "thumb"}).status_code == 404
    # Unversioned URLs aren't cached for good
    assert "cache-control" not in client.get(f"/api/tastings/photos/Odette_{DAY}.jpg").headers


def test_photos_follow_a_renamed_place(client, photo_dir):
    """Renaming a place in its form renames its photos ("<place>_<date>"), so they keep showing."""
    assert put(client, JPEG).status_code == 200
    tasting = client.get("/api/tastings").json()["tastings"][0]
    pid = tasting["place_id"]
    assert client.put(f"/api/places/{pid}", json={"name": "Odette (Singapore)", "city": "Singapore"}).status_code == 200
    assert sorted(os.listdir(photo_dir)) == [f"Odette (Singapore)_{DAY}.jpg"]
    assert url(client, "Odette (Singapore)") and not url(client, "Odette")
    assert client.get(f"/api/tastings/{tasting['id']}").json()["photo"]  # still on the tasting
    client.put(f"/api/places/{pid}", json={"name": "Odette", "city": "Singapore"})  # as the other tests expect


def test_rename_keeps_a_photo_already_there(photo_dir):
    os.makedirs(photo_dir)
    for name in (f"A_{DAY}.jpg", f"B_{DAY}.png", "A_notes.jpg", f"AB_{DAY}.jpg"):
        (photo_dir / name).write_bytes(JPEG)
    assert photos.rename_place("A", "B") == 0  # B already has that day's photo
    assert photos.rename_place("a", "C") == 1  # matched case-insensitively; AB_ and A_notes aren't A's
    assert sorted(os.listdir(photo_dir)) == ["AB_2024-03-01.jpg", "A_notes.jpg", f"B_{DAY}.png", f"C_{DAY}.jpg"]
