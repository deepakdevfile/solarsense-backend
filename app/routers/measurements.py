from datetime import datetime 

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.auth import get_current_user
from app.db import get_db
from app.models import User, Installation, Measurement
from app.schemas import MeasurementOut, ImportResult
from app.services.measurement_services import import_measurements

router = APIRouter(tags=["measurements"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024

@router.get("/measurements", response_model=list[MeasurementOut])
def list_measurement(
    installation_id: int | None = None,
    start: datetime | None = None,
    end: datetime | None = None, 
    limit: int = Query(500, ge=1, le=5000),
    user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    query = select(Measurement).join(Installation).where(Installation.owner_id == user.id)
    if installation_id is not None:
        query = query.where(Measurement.installation_id == installation_id)
    if start:
        query = query.where(Measurement.measured_at >= start)
    if end:
        query = query.where(Measurement.measured_at <= end)
    rows = db.scalars(query.order_by(Measurement.measured_at.desc()).limit(limit)).all()
    return list(reversed(rows))

@router.get("/measurement/{measurement_id}", response_model=MeasurementOut)
def get_measurement(measurement_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.scalar(
        select(Measurement).join(Installation).where(Measurement.id == measurement_id, Installation.owner_id == user.id)
    )
    if not row: 
        raise HTTPException(404, "Measurement not found")
    return row

@router.post("/measurement/import/{id}", response_model = ImportResult)
def import_csv(
    id: int, 
    file: UploadFile = File(...), 
    tz: str = Query("UTC", description="IANA timezone of timestamp that carry no UTC offset"),
    user: User = Depends(get_current_user), 
    db: Session = Depends(get_db),
):
    # print("imports recieved") #issue can be caused by "content-type" in request from frontend
    # print(id)
    installation = db.scalar(select(Installation).where(Installation.id == id, Installation.owner_id == user.id))
    if not installation:
        raise HTTPException(404, "Installation not found")
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Upload a .csv file")
    # print("file name and installation exits")
    try:
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(422, f"Unknown timezone: {tz}")
    file.file.seek(0, 2)
    if file.file.tell() > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "CSV is larger than 10 MB")
    file.file.seek(0)
    inserted, skipped, rejected, errors = import_measurements(db, installation, file.file, tz)
    return ImportResult(inserted = inserted, skipped_duplicates = skipped, rejected = rejected, errors = errors)