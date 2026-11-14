"""Occasion photos: look up, upload (raw image body) and remove the photo of a place on a day. Wines' labels too."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

import photos
from db import Wine, get_session

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


@router.put("/api/wines/{wine_id}/label")
async def put_label(wine_id: int, request: Request, session: Session = Depends(get_session)):
    """A wine's label: a photo or a scan (JPEG, PNG, WebP) or a drawing (SVG), the raw image as the body."""
    if session.get(Wine, wine_id) is None:
        raise HTTPException(404, "Wine not found")
    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if content_type not in photos.LABEL_TYPES:
        raise HTTPException(415, "Labels must be JPEG, PNG, WebP or SVG")
    data = await request.body()
    if not data:
        raise HTTPException(422, "The label is empty")
    if len(data) > photos.MAX_UPLOAD:
        raise HTTPException(413, f"Labels can be up to {photos.MAX_UPLOAD // 1024 // 1024} MB")
    return {"url": photos.url_for(photos.save_label(wine_id, data, content_type))}


@router.delete("/api/wines/{wine_id}/label")
def delete_label(wine_id: int):
    return {"deleted": photos.delete_label(wine_id)}


@router.post("/api/wines/{wine_id}/label/spares/{name}")
def use_spare_label(wine_id: int, name: str):
    """A label kept aside from a merge becomes the wine's (the one it had is kept aside in its place)."""
    new = photos.use_spare(wine_id, name)
    if new is None:
        raise HTTPException(404, "No such label kept for this wine")
    return {"url": photos.url_for(new)}


@router.delete("/api/wines/{wine_id}/label/spares/{name}")
def delete_spare_label(wine_id: int, name: str):
    if not photos.delete_spare(wine_id, name):
        raise HTTPException(404, "No such label kept for this wine")
    return {"deleted": name}


@router.delete("/api/photos")
def delete_photo(place: str, date: date):
    _check(place)
    return {"deleted": photos.delete_photo(place, date)}
