from datetime import datetime, timedelta, timezone
import jwt
from .config import settings
from fastapi import Request, Depends, HTTPException, status, Response
from app.db import get_db
from sqlalchemy.orm import Session
from app.models import User
import bcrypt

ALGORITHM = "HS256"
COOKIE_NAME = "access_token"
COOKIE_MAX_AGE = 86400

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except ValueError:
        return False

def create_token(user_id: int) -> str:
    payload = {"sub": str(user_id), "exp": datetime.now(timezone.utc) + timedelta(hours = 24)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)

def set_auth_cookie(response: Response, user_id: int) -> str:
    # print("okay2")
    response.set_cookie(
        COOKIE_NAME, create_token(user_id), httponly=True, 
        secure=settings.cookie_secure, samesite=settings.cookie_samesite, 
        max_age=COOKIE_MAX_AGE, path="/")

def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(COOKIE_NAME)
    # print(request.headers)
    # print(request.cookies)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try: 
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except( jwt.InvalidTokenError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user