"""
Authentication routes — student signup / login, admin login, logout.
"""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Student, Admin
from app.auth import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="app/templates")


# ─── Student Auth ─────────────────────────────────────────────────────────────

@router.get("/student/login")
async def student_login_page(request: Request):
    return templates.TemplateResponse("student/login.html", {"request": request})


@router.post("/student/login")
async def student_login(
    request: Request,
    roll_number: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    student = db.query(Student).filter(Student.roll_number == roll_number).first()
    if not student or not verify_password(password, student.password_hash):
        return templates.TemplateResponse(
            "student/login.html",
            {"request": request, "error": "Invalid roll number or password"},
        )

    token = create_access_token({"sub": str(student.id), "role": "student", "name": student.name})
    response = RedirectResponse(url="/student/dashboard", status_code=302)
    response.set_cookie(key="access_token", value=token, httponly=True, max_age=86400, samesite="lax")
    return response


@router.get("/student/signup")
async def student_signup_page(request: Request):
    return templates.TemplateResponse("student/signup.html", {"request": request})


@router.post("/student/signup")
async def student_signup(
    request: Request,
    name: str = Form(...),
    roll_number: str = Form(...),
    department: str = Form(...),
    year: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    if db.query(Student).filter(Student.roll_number == roll_number).first():
        return templates.TemplateResponse(
            "student/signup.html",
            {"request": request, "error": "Roll number already registered"},
        )

    student = Student(
        name=name,
        roll_number=roll_number,
        department=department,
        year=year,
        password_hash=hash_password(password),
    )
    db.add(student)
    db.commit()
    db.refresh(student)

    token = create_access_token({"sub": str(student.id), "role": "student", "name": student.name})
    response = RedirectResponse(url="/student/dashboard", status_code=302)
    response.set_cookie(key="access_token", value=token, httponly=True, max_age=86400, samesite="lax")
    return response


# ─── Admin Auth ───────────────────────────────────────────────────────────────

@router.get("/admin/login")
async def admin_login_page(request: Request):
    return templates.TemplateResponse("admin/login.html", {"request": request})


@router.post("/admin/login")
async def admin_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    admin = db.query(Admin).filter(Admin.email == email).first()
    if not admin or not verify_password(password, admin.password_hash):
        return templates.TemplateResponse(
            "admin/login.html",
            {"request": request, "error": "Invalid email or password"},
        )

    token = create_access_token({"sub": str(admin.id), "role": "admin", "name": admin.name})
    response = RedirectResponse(url="/admin/dashboard", status_code=302)
    response.set_cookie(key="access_token", value=token, httponly=True, max_age=86400, samesite="lax")
    return response


# ─── Logout ───────────────────────────────────────────────────────────────────

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("access_token")
    return response
