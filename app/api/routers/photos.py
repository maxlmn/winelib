"""Occasion photos: look up, upload (raw image body) and remove the photo of a place on a day."""
from datetime import date

from fastapi import APIRouter, HTTPException, Request

import photos

router = APIRouter()


def _check(place: str):
    if not place.strip():
        raise HTTPException(422, "Pick a place first: photos are filed by place and date")


@router.get("/api/photos")
def get_photo(place: str, date: date):
    return {"url": photos.photo_url(photos.photo_index(), place, date)}


@router.put("/api/photos")
async def put_photo(place: str, date: date, request: Request):
    _check(place)
    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if content_type not in photos.UPLOAD_TYPES:
        raise HTTPException(415, "Photos must be JPEG, PNG, WebP or GIF")
    data = await request.body()
    if not data:
        raise HTTPException(422, "The photo is empty")
    if len(data) > photos.MAX_UPLOAD:
        raise HTTPException(413, f"Photos can be up to {photos.MAX_UPLOAD // 1024 // 1024} MB")
    name = photos.save_photo(place, date, data, content_type)
    return {"url": photos.url_for(name)}


@router.delete("/api/photos")
def delete_photo(place: str, date: date):
    _check(place)
    return {"deleted": photos.delete_photo(place, date)}
