from fastapi import APIRouter, Depends, HTTPException
from app.schemas import WeatherOut
from app.auth import get_current_user
from app.models import User, Installation, WeatherObservation
from sqlalchemy.orm import Session
from app.db import get_db
from sqlalchemy import select
from app.services.weather_services import sync_weather

router = APIRouter(tags={"Weather"})

@router.get("/weather/{id}", response_model=list[WeatherOut])
def list_weather(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    installation_row = db.scalar(select(Installation).where(Installation.id == id, Installation.owner_id == user.id))
    if not installation_row:
        raise HTTPException(404, "Installation not found")
    return db.scalars(select(WeatherObservation).where(WeatherObservation.installation_id == id).order_by(WeatherObservation.observed_at)).all()

@router.post("/weather/{id}/sync")
def weather_sync(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    installation_row = db.scalar(select(Installation).where(Installation.id == id, Installation.owner_id == user.id))
    if not installation_row:
        raise HTTPException(404, "Installation not found")
    try:
        count = sync_weather(db, installation_row)
    except Exception as exc:
        raise HTTPException(502, f"Weather provider request failed: {exc}")
    return {"inserted": count}