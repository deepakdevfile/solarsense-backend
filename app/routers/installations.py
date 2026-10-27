from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import Installation, User, Measurement, WeatherObservation
from app.schemas import InstallationCreate, InstallationOut, MeasurementCreate, MeasurementOut, InstallationSummary

router = APIRouter(tags=["Installations"])

def owned_installation(db: Session, installation_id: int, user: User) -> Installation:
    installation = db.scalar(select(Installation).where(Installation.id == installation_id, Installation.owner_id == user.id))
    if not installation: 
        raise HTTPException(404, "Installation not found")
    return installation

@router.post("/installation", response_model=InstallationOut, status_code=201)
def add_installation(payload: InstallationCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    installation = Installation(**payload.model_dump(), owner_id = user.id)
    db.add(installation)
    db.commit()
    db.refresh(installation)
    return installation

@router.get("/installation", response_model=list[InstallationOut])
def list_installation(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    installation = db.scalars(select(Installation).where(Installation.owner_id == user.id).order_by(Installation.id.desc())).all()
    # print(installation)
    return installation

@router.get("/installation/{id}", response_model=InstallationOut)
def get_installation(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return owned_installation(db, id, user)

@router.put("/installation/{id}", response_model=InstallationOut)
def update_installation(id: int, payload: InstallationCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    installation = owned_installation(db, id, user)
    installation.name = payload.name
    installation.location = payload.location
    installation.latitude = payload.latitude
    installation.longitude = payload.longitude
    installation.capacity = payload.capacity
    db.commit()
    db.refresh(installation)
    return installation

@router.delete("/installation/{id}", status_code=204)
def delete_installation(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    installation = owned_installation(db, id, user)
    db.delete(installation)
    db.commit()

@router.get("/installation/{id}/summary", response_model=InstallationSummary)
def installation_summary(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    owned_installation(db, id, user)
    count, total, peak, first, last = db.execute(
        select(
            func.count(Measurement.id),
            func.coalesce(func.sum(Measurement.energy_kwh), 0.0),
            func.coalesce(func.max(Measurement.power_kw), 0.0),
            func.min(Measurement.measured_at),
            func.max(Measurement.measured_at),
        ).where(Measurement.installation_id == id)
    ).one()
    weather_count = db.scalar(
        select(func.count(WeatherObservation.id)).where(WeatherObservation.installation_id == id)
    )
    return InstallationSummary(
        measurement_count = count, 
        total_energy_kwh = float(total), 
        peak_power_kw = float(peak),
        first_measured_at = first,
        last_measured_at = last,
        weather_count = weather_count or 0,
    )

@router.post("/installation/{id}/measurements", response_model=MeasurementOut, status_code=201)
def create_measurement(id: int, payload: MeasurementCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    installation = owned_installation(db, id, user)
    measured_at = payload.measured_at or datetime.now(timezone.utc)
    if measured_at.tzinfo is None: 
        measured_at = measured_at.replace(tzinfo = timezone.utc)
    if payload.power_kw > installation.capacity * 1.5:
        raise HTTPException(422, "Power is implausibly high for installation capacity")
    exists = db.scalar(select(Measurement.id).where(Measurement.installation_id == id, Measurement.measured_at == measured_at))
    if exists:
        raise HTTPException(409, "Measurement already exists")
    measurement = Measurement(energy_kwh = payload.energy_kwh, power_kw = payload.power_kw, measured_at = measured_at, installation_id = id,)
    db.add(measurement)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Measurement already exists")
    db.refresh(measurement)
    return measurement
