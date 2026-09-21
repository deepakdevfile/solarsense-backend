from fastapi import APIRouter, Depends
from app.schemas import InstallationCreate, InstallationOut
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Installation

router = APIRouter()

@router.post("/installation", response_model=InstallationOut, status_code=201)
def add_installation(payload: InstallationCreate, db: Session = Depends(get_db)):
    installation = Installation(**payload.model_dump())
    db.add(installation)
    db.commit()
    db.refresh(installation)
    return installation