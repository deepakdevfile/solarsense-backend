from fastapi import APIRouter
from app.schemas import InstallationCreate

router = APIRouter()

@router.post("/installation")
def add_installation(payload: InstallationCreate):
    print(payload)
    return {"okay"}