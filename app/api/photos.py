"""Occasion photos: one per place and day, stored as "<place name>_<YYYY-MM-DD>.<ext>" in PHOTOS_DIR,
matched case-insensitively.

Originals are full-size phone photos, so pages show resized copies (see thumbnail): made on first request and
cached in THUMBS_DIR, keyed by the source's mtime and size so a replaced photo never shows a stale one. Photo URLs
carry a version (?v=, the source's mtime) so browsers can cache them forever; add &size=thumb|large for a copy."""
import os
import threading
import re
from urllib.parse import quote

import paths
from display import iso

PHOTOS_DIR = paths.PHOTOS_DIR
PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}
# What uploads may be; SVG is served if already there but not accepted (it can carry scripts)
UPLOAD_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}
MAX_UPLOAD = 15 * 1024 * 1024

THUMBS_DIR = paths.THUMBS_DIR
# Long side in pixels: lists and cards, and the photo shown big on a detail page
THUMB_SIZES = {"thumb": 480, "large": 1600}
THUMB_QUALITY = 80


def stem(place, day):
    """File name without extension; path separators can't appear in it."""
    name = (place or "").strip().replace("/", "-").replace("\\", "-").replace("\0", "")
    if os.name == "nt":  # what Windows can't put in a file name ("Bar: Le Comptoir"; a ":" makes a hidden stream)
        name = re.sub(r'[<>:"|?*\x00-\x1f]', "-", name).rstrip(". ")
    return f"{name}_{iso(day)}"


def photo_index():
    """Lowercased "<place>_<date>" -> file name."""
    if not os.path.isdir(PHOTOS_DIR):
        return {}
    index = {}
    for name in sorted(os.listdir(PHOTOS_DIR)):
        base, ext = os.path.splitext(name)
        if ext.lower() in PHOTO_EXTS:
            index.setdefault(base.lower(), name)
    return index


def url_for(name):
    """The served URL of a file in PHOTOS_DIR, versioned by its mtime (it changes when the photo is replaced)."""
    try:
        version = os.stat(os.path.join(PHOTOS_DIR, name)).st_mtime_ns // 1_000_000
    except OSError:
        return f"/api/tastings/photos/{quote(name)}"
    return f"/api/tastings/photos/{quote(name)}?v={version}"


def photo_url(index, place, day):
    name = index.get(stem(place, day).lower())
    return url_for(name) if name else None


def thumbnail(name, size):
    """Path of a resized JPEG copy of PHOTOS_DIR/name (long side THUMB_SIZES[size]), made and cached on first use.
    Raises (OSError, Pillow errors) when the file can't be read as an image; callers serve the original then."""
    from PIL import Image, ImageOps  # only needed here

    src = os.path.join(PHOTOS_DIR, name)
    st = os.stat(src)
    path = os.path.join(THUMBS_DIR, f"{name}~{st.st_mtime_ns}-{st.st_size}~{size}.jpg")
    if os.path.isfile(path):
        return path
    box = THUMB_SIZES[size]
    with Image.open(src) as img:
        img.draft("RGB", (box, box))  # JPEGs decode at a reduced scale: much faster for phone photos
        img = ImageOps.exif_transpose(img)  # phones store sideways pixels plus an orientation tag
        if img.mode in ("RGBA", "LA", "P", "PA"):  # transparency goes on white, not black
            img = img.convert("RGBA")
            flat = Image.new("RGB", img.size, "white")
            flat.paste(img, mask=img.getchannel("A"))
            img = flat
        img = img.convert("RGB")
        img.thumbnail((box, box), Image.LANCZOS)  # never enlarges
        os.makedirs(THUMBS_DIR, exist_ok=True)
        tmp = f"{path}.{os.getpid()}.{threading.get_ident()}.part"  # two requests for one thumbnail: a file each
        img.save(tmp, "JPEG", quality=THUMB_QUALITY, optimize=True, progressive=True)
    os.replace(tmp, path)
    return path


def _drop_thumbs(place, day):
    """Best effort: removes the cached copies of an occasion's photo (they'd never be served again anyway)."""
    key = stem(place, day).lower()
    try:
        for name in os.listdir(THUMBS_DIR):
            if os.path.splitext(name.rsplit("~", 2)[0])[0].lower() == key:
                os.remove(os.path.join(THUMBS_DIR, name))
    except OSError:
        pass


def _existing(place, day):
    key = stem(place, day).lower()
    if not os.path.isdir(PHOTOS_DIR):
        return []
    return [n for n in os.listdir(PHOTOS_DIR)
            if os.path.splitext(n)[0].lower() == key and os.path.splitext(n)[1].lower() in PHOTO_EXTS]


def save_photo(place, day, data, content_type):
    """Replaces the occasion's photo (whatever its previous format) and returns the new file name."""
    os.makedirs(PHOTOS_DIR, exist_ok=True)
    name = stem(place, day) + UPLOAD_TYPES[content_type]
    tmp = os.path.join(PHOTOS_DIR, f".{name}.part")
    with open(tmp, "wb") as f:
        f.write(data)
    for old in _existing(place, day):
        os.remove(os.path.join(PHOTOS_DIR, old))
    os.replace(tmp, os.path.join(PHOTOS_DIR, name))
    _drop_thumbs(place, day)
    return name


def rename_place(old, new):
    """A renamed place's photos follow it: every "<old>_<date>" file becomes "<new>_<date>" (one already there under
    the new name is kept, the old one left as it was). The number renamed."""
    if not os.path.isdir(PHOTOS_DIR) or stem(old, "").lower() == stem(new, "").lower():
        return 0
    pattern = re.compile(re.escape(stem(old, "")) + r"(\d{4}-\d{2}-\d{2})", re.IGNORECASE)
    renamed = 0
    for name in os.listdir(PHOTOS_DIR):
        base, ext = os.path.splitext(name)
        m = pattern.fullmatch(base)
        if not m or ext.lower() not in PHOTO_EXTS:
            continue
        day = m.group(1)
        if _existing(new, day):
            continue
        os.replace(os.path.join(PHOTOS_DIR, name), os.path.join(PHOTOS_DIR, stem(new, day) + ext))
        _drop_thumbs(old, day)
        renamed += 1
    return renamed


def delete_photo(place, day):
    removed = _existing(place, day)
    for name in removed:
        os.remove(os.path.join(PHOTOS_DIR, name))
    _drop_thumbs(place, day)
    return bool(removed)
