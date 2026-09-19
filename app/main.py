from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .schemas import AuthPayload, UserOut
from sqlalchemy.orm import Session
from .db import get_db, Base, engine
from sqlalchemy import select
from .models import User

Base.metadata.create_all(bind=engine)
app = FastAPI(title = "SolarSense API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=False,
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