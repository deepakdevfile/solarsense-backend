from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from app.schemas import MeasurementOut, ImportResult
from app.models import User, Installation, Measurement
from app.auth import get_current_user
from app.db import get_db
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.services.measurement_services import import_measurements

router = APIRouter(tags=["measurements"])

@router.get("/measurements", response_model=list[MeasurementOut])
def list_measurement(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    measurements = select(Measurement).join(Installation).where(Installation.owner_id == user.id)
    return db.scalars(measurements.order_by(Measurement.measured_at)).all()

@router.get("/measuremet/{id}", response_model=MeasurementOut)
def get_measurement(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    measurement = select(Measurement).join(Installation).where(Measurement.installation_id == id, Installation.owner_id == user.id)
    # return db.scalars(q.order_by(Measurement.measured_at)).all()
    return measurement

@router.post("/measurement/import/{id}", response_model = ImportResult)
def import_csv(id: int, file: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # print("imports recieved") #issue can be caused by "content-type" in request from frontend
    # print(id)
    installation_row = db.scalar(select(Installation).where(Installation.id == id, Installation.owner_id == user.id))
    if not installation_row:
        raise HTTPException(404, "Installation not found")
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(404, "Upload a CSV file")
    # print("file name and installation exits")
    i, s, r, e = import_measurements(db, installation_row, file.file)
    return ImportResult(inserted = i, skipped_duplicates = s, rejected= r, errors= e)