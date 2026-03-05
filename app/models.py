"""
SQLAlchemy ORM models for the Campus GatePass System.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base

# ─── Constants ────────────────────────────────────────────────────────────────

DEPARTMENTS = ["CS", "IT", "ENTC", "MECH", "CIVIL", "AI&DS"]
YEARS = ["First Year", "Second Year", "Third Year", "Final Year"]
PASS_STATUSES = ["Pending", "Approved", "Rejected", "Expired", "Cancelled"]


# ─── Student ──────────────────────────────────────────────────────────────────

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    roll_number = Column(String(20), unique=True, nullable=False, index=True)
    department = Column(String(10), nullable=False)
    year = Column(String(20), nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    gatepasses = relationship("GatePass", back_populates="student")


# ─── Admin ────────────────────────────────────────────────────────────────────

class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="admin")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ─── GatePass ─────────────────────────────────────────────────────────────────

class GatePass(Base):
    __tablename__ = "gatepasses"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    reason = Column(Text, nullable=False)
    date = Column(String(20), nullable=False)
    out_time = Column(String(10), nullable=False)
    return_time = Column(String(10), nullable=False)
    status = Column(String(20), default="Pending", index=True)
    qr_token = Column(String(100), unique=True, nullable=True, index=True)
    approved_by = Column(Integer, ForeignKey("admins.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    student = relationship("Student", back_populates="gatepasses")
    approver = relationship("Admin", foreign_keys=[approved_by])
