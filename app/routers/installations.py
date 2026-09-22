from fastapi import APIRouter, Depends, HTTPException
from app.schemas import InstallationCreate, InstallationOut
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Installation
from sqlalchemy import select

router = APIRouter(tags=["Installations"])

@router.post("/installation", response_model=InstallationOut, status_code=201)
def add_installation(payload: InstallationCreate, db: Session = Depends(get_db)):
    installation = Installation(**payload.model_dump())
    db.add(installation)
    db.commit()
    db.refresh(installation)
    return installation

@router.get("/installation", response_model=list[InstallationOut])
def list_installation(db: Session = Depends(get_db)):
    installation = db.scalars(select(Installation)).all()
    # print(installation)
    return installation

@router.get("/installation/{id}", response_model=InstallationOut, status_code=201)
def get_installation(id: int, db: Session = Depends(get_db)):
    installation = db.scalar(select(Installation).where(Installation.id == id))
    if not installation: 
        raise HTTPException(404, "Installation not found")
    return installation

@router.put("/installation/{id}", response_model=InstallationOut, status_code=200)
def update_installation(id: int, payload: InstallationCreate, db: Session = Depends(get_db)):
    installation = db.scalar(select(Installation).where(Installation.id == id))
    if not installation: 
        raise HTTPException(404, "Installation not found")
    installation.name = payload.name
    installation.location = payload.location
    installation.capacity = payload.capacity
    db.add(installation)
    db.commit()
    db.refresh(installation)
    return installation