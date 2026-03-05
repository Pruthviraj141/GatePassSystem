"""
Pydantic schemas for request / response validation.
"""

from pydantic import BaseModel
from typing import Optional


class StudentCreate(BaseModel):
    name: str
    roll_number: str
    department: str
    year: str
    password: str


class StudentLogin(BaseModel):
    roll_number: str
    password: str


class AdminCreate(BaseModel):
    name: str
    email: str
    password: str
    role: str = "admin"


class AdminLogin(BaseModel):
    email: str
    password: str


class GatePassCreate(BaseModel):
    reason: str
    date: str
    out_time: str
    return_time: str
