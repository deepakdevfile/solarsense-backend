from fastapi import APIRouter, Depends
from app.schemas import MeasurementOut
from app.models import User, Installation, Measurement
from app.auth import get_current_user
from app.db import get_db
from sqlalchemy.orm import Session
from sqlalchemy import select

router = APIRouter(tags=["measurements"])

@router.get("/measurements", response_model=list[MeasurementOut])
def get_measurement(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    measurements = select(Measurement).join(Installation).where(Installation.owner_id == user.id)
    return db.scalars(measurements.order_by(Measurement.measured_at)).all()

@router.get("/measuremet/{id}", response_model=MeasurementOut)
def get_measurement(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    measurement = select(Measurement).join(Installation).where(Measurement.installation_id == id, Installation.owner_id == user.id)
    # return db.scalars(q.order_by(Measurement.measured_at)).all()
    return measurement