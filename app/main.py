from fastapi import FastAPI, Depends, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .schemas import AuthPayload, UserOut
from sqlalchemy.orm import Session
from .db import get_db, Base, engine
from sqlalchemy import select
from .models import User
from .auth import verify_password, create_token
from .config import settings

Base.metadata.create_all(bind=engine)
app = FastAPI(title = "SolarSense API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Hello from backend"}

@app.post("/auth/register", response_model=UserOut, status_code=201)
def register_user(payload: AuthPayload, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == payload.email.lower())):
        raise HTTPException(409, "Email already registered")
    user = User(email = payload.email.lower(), password_hash = payload.password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@app.post("/auth/login", response_model=UserOut)
def login_user(payload: AuthPayload, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    response.set_cookie("access_token", create_token(user.id), httponly = True, secure = settings.cookie_secure, samesite = "lax", max_age = 86400)
    return user

@app.post("/auth/logout", status_code=204)
def logout_user(response: Response):
    response.delete_cookie("access_token")
    return {"message": "user session cookies are deleted"}