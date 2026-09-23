from fastapi import Depends, HTTPException, Response, APIRouter 
from pydantic import BaseModel
from ..schemas import AuthPayload, UserOut
from sqlalchemy.orm import Session
from ..db import get_db
from sqlalchemy import select
from ..models import User
from ..auth import verify_password, create_token, get_current_user, hash_password
from ..config import settings

router = APIRouter(tags=["Users"])

@router.post("/auth/register", response_model=UserOut, status_code=201)
def register_user(payload: AuthPayload, response: Response, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == payload.email.lower())):
        raise HTTPException(409, "Email already registered")
    user = User(email = payload.email.lower(), password_hash = hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    response.set_cookie("access_token", create_token(user.id), httponly = True, secure = settings.cookie_secure, samesite = "lax", max_age = 86400)
    return user

@router.post("/auth/login", response_model=UserOut)
def login_user(payload: AuthPayload, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    response.set_cookie("access_token", create_token(user.id), httponly = True, secure = settings.cookie_secure, samesite = "lax", max_age = 86400)
    return user

@router.get("/auth/current", response_model=UserOut)
def current_user(user: User = Depends(get_current_user)):
    return user
    

@router.post("/auth/logout", status_code=204)
def logout_user(response: Response):
    response.delete_cookie("access_token")