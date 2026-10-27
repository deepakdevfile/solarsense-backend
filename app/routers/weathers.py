from datetime import date, datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import User, Installation, WeatherObservation
from app.schemas import WeatherOut, WeatherSyncResult

from app.services.weather_services import sync_weather

router = APIRouter(tags=["Weather"])

def _owned(db: Session, id: int, user: User) -> Installation:
    installation = db.scalar(select(Installation).where(Installation.id == id, Installation.owner_id == user.id))
    if not installation:
        raise HTTPException(404, "Installation not found")
    return installation

@router.get("/weather/{id}", response_model=list[WeatherOut])
def list_weather(
    id: int, 
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(500, ge = 1, le = 5000),
    user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    _owned(db, id, user)
    query = select(WeatherObservation).where(WeatherObservation.installation_id == id)
    if start: 
        query = query.where(WeatherObservation.observed_at >= start)
    if end: 
        query = query.where(WeatherObservation.observed_at <= end)
    rows = db.scalar(query.order_by(WeatherObservation.observed_at.desc()).limit(limit)).all()
    return list(reversed(rows))

@router.post("/weather/{id}/sync", response_model=WeatherSyncResult)
def weather_sync(
    id: int, 
    start_date: date | None = None,
    end_date: date | None = None,
    user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    installation = _owned(db, id, user)
    if (start_date is None) != (end_date is None):
        raise HTTPException(422, "Provide both start_date and end_date, or neither")
    try:
        count, source = sync_weather(db, installation, start_date, end_date)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    except httpx.HTTPError:
        db.rollback()
        raise HTTPException(502, f"Weather provider request failed. Try again in a moment.")
    return WeatherSyncResult(upserted = count, source = source)