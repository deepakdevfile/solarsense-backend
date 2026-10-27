from fastapi import Depends, HTTPException, Response, APIRouter 
from pydantic import BaseModel
from app.schemas import UserOut, RegisterPayload, LoginPayload
from sqlalchemy.orm import Session
from ..db import get_db
from sqlalchemy import select
from ..models import User
from app.auth import verify_password, create_token, get_current_user, hash_password, set_auth_cookie, clear_auth_cookie
from ..config import settings

router = APIRouter(tags=["Users"])

@router.post("/auth/register", response_model=UserOut, status_code=201)
def register_user(payload: RegisterPayload, response: Response, db: Session = Depends(get_db)):
    email = payload.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "Email already registered")
    user = User(name = payload.name.strip(), email = email, password_hash = hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    # print("okay1")
    set_auth_cookie(response, user.id)
    # print(response.headers)
    return user

@router.post("/auth/login", response_model=UserOut)
def login_user(payload: LoginPayload, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    set_auth_cookie(response, user.id)
    return user

@router.get("/auth/current", response_model=UserOut)
def current_user(user: User = Depends(get_current_user)):
    return user
    

@router.post("/auth/logout", status_code=204)
def logout_user(response: Response):
    clear_auth_cookie(response)