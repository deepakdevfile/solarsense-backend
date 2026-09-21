from datetime import datetime, timedelta, timezone
import jwt
from .config import settings
from fastapi import Request, Depends, HTTPException, status
from app.db import get_db
from sqlalchemy.orm import Session
from app.models import User

ALGORITHM = "HS256"

def verify_password(password: str, password_hash: str) -> bool:
    return password == password_hash

def create_token(user_id: int) -> str:
    payload = {"sub": str(user_id), "exp": datetime.now(timezone.utc) + timedelta(hours = 24)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)

