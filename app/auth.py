"""
Authentication utilities — password hashing, JWT tokens, session helpers.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import Request
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.models import Student, Admin

# ─── Configuration ────────────────────────────────────────────────────────────

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "campus-gatepass-secret-key-change-in-production-2024",
)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24


# ─── Password helpers ─────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


# ─── JWT helpers ──────────────────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


# ─── Session helpers (cookie-based JWT) ───────────────────────────────────────

def get_student_from_token(request: Request, db: Session) -> Optional[Student]:
    """Extract the authenticated student from the request cookie, or None."""
    token = request.cookies.get("access_token")
    if not token:
        return None
    payload = decode_token(token)
    if not payload or payload.get("role") != "student":
        return None
    student_id = payload.get("sub")
    if not student_id:
        return None
    return db.query(Student).filter(Student.id == int(student_id)).first()


def get_admin_from_token(request: Request, db: Session) -> Optional[Admin]:
    """Extract the authenticated admin from the request cookie, or None."""
    token = request.cookies.get("access_token")
    if not token:
        return None
    payload = decode_token(token)
    if not payload or payload.get("role") != "admin":
        return None
    admin_id = payload.get("sub")
    if not admin_id:
        return None
    return db.query(Admin).filter(Admin.id == int(admin_id)).first()
