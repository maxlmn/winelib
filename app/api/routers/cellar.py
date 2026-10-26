"""Cellar inventory and region colors."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from cellar import load_cellar
from db import Region, get_session

router = APIRouter()


@router.get("/api/regions")
def regions(session: Session = Depends(get_session)):
    return {r.name: r.color for r in session.query(Region).all() if r.color}


@router.get("/api/region-countries")
def region_countries(session: Session = Depends(get_session)):
    """{region: country} for the regions named apart from their country: the app shows "Mosel, Germany"."""
    return {r.name: r.country for r in session.query(Region).all() if r.country and r.country != r.name}


@router.get("/api/cellar")
def cellar(session: Session = Depends(get_session)):
    bottles, locations = load_cellar(session)
    return {"bottles": bottles, "locations": locations}
