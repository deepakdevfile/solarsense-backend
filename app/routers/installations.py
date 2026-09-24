from fastapi import APIRouter, Depends, HTTPException
from app.schemas import InstallationCreate, InstallationOut, MeasurementCreate, MeasurementOut
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Installation, User, Measurement
from sqlalchemy import select
from app.auth import get_current_user
from datetime import datetime, timezone

router = APIRouter(tags=["Installations"])

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

@router.get("/installation/{id}", response_model=InstallationOut, status_code=201)
def get_installation(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    installation = db.scalar(select(Installation).where(Installation.id == id, Installation.owner_id == user.id))
    if not installation: 
        raise HTTPException(404, "Installation not found")
    return installation

@router.put("/installation/{id}", response_model=InstallationOut)
def update_installation(id: int, payload: InstallationCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    installation = db.scalar(select(Installation).where(Installation.id == id, Installation.owner_id == user.id))
    if not installation: 
        raise HTTPException(404, "Installation not found")
    installation.name = payload.name
    installation.location = payload.location
    installation.capacity = payload.capacity
    db.add(installation)
    db.commit()
    db.refresh(installation)
    return installation

@router.delete("/installation/{id}", status_code=204)
def delete_installation(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    installation = db.scalar(select(Installation).where(Installation.id == id, Installation.owner_id == user.id))
    if not installation:
        raise HTTPException(404, "Installation not found")
    db.delete(installation)
    db.commit()

@router.post("/installation/{id}/measurements", response_model=MeasurementOut, status_code=201)
def create_measurement(id: int, payload: MeasurementCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    measurement_row = db.scalar(select(Installation).where(Installation.id == id, Installation.owner_id == user.id))
    if not measurement_row:
        raise HTTPException(404, "Installation not found")
    measured_at = payload.measured_at or datetime.now(timezone.utc)
    if payload.power_kw > measurement_row.capacity*1.5:
        raise HTTPException(422, "Power is implausibly high for installation capacity")
    if db.scaler(select(Measurement).where(Measurement.id == id, Measurement.measured_at == measured_at)):
        raise HTTPException(409, "Measurement already exists")
    measurement = Measurement(**payload.model_dump(exclude = {"measured_at"}), measured_at = measured_at, installation_id = id)
    db.add(measurement)
    db.commit()
    db.refresh(measurement)
    return measurement
