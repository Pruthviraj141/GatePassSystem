"""
Student routes — dashboard, raise pass, view pass, cancel, history, PDF download.
"""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, StreamingResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import GatePass
from app.auth import get_student_from_token
from app.services.qr_service import generate_qr_code_base64
from app.services.pdf_service import generate_pass_pdf
from app.services.gatepass_service import has_active_pass, get_active_pass
from app.routes.websocket_routes import manager

router = APIRouter(prefix="/student", tags=["student"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/dashboard")
async def dashboard(request: Request, db: Session = Depends(get_db)):
    student = get_student_from_token(request, db)
    if not student:
        return RedirectResponse(url="/auth/student/login")

    active_pass = get_active_pass(db, student.id)
    recent_passes = (
        db.query(GatePass)
        .filter(GatePass.student_id == student.id)
        .order_by(GatePass.created_at.desc())
        .limit(5)
        .all()
    )

    qr_data = None
    if active_pass and active_pass.qr_token:
        verify_url = str(request.base_url) + f"verify/{active_pass.qr_token}"
        qr_data = generate_qr_code_base64(verify_url)

    return templates.TemplateResponse("student/dashboard.html", {
        "request": request,
        "student": student,
        "active_pass": active_pass,
        "recent_passes": recent_passes,
        "qr_data": qr_data,
    })


@router.get("/raise-pass")
async def raise_pass_page(request: Request, db: Session = Depends(get_db)):
    student = get_student_from_token(request, db)
    if not student:
        return RedirectResponse(url="/auth/student/login")

    return templates.TemplateResponse("student/raise_pass.html", {
        "request": request,
        "student": student,
        "has_active": has_active_pass(db, student.id),
    })


@router.post("/raise-pass")
async def raise_pass(
    request: Request,
    reason: str = Form(...),
    date: str = Form(...),
    out_time: str = Form(...),
    return_time: str = Form(...),
    whole_day: str = Form(None),
    db: Session = Depends(get_db),
):
    student = get_student_from_token(request, db)
    if not student:
        return RedirectResponse(url="/auth/student/login")

    if has_active_pass(db, student.id):
        return templates.TemplateResponse("student/raise_pass.html", {
            "request": request,
            "student": student,
            "has_active": True,
            "error": "You already have an active gate pass request.",
        })

    # If 'whole_day' flag is set, treat return_time as end of day (23:59)
    if whole_day:
        return_time = "23:59"

    gatepass = GatePass(
        student_id=student.id,
        reason=reason,
        date=date,
        out_time=out_time,
        return_time=return_time,
        status="Pending",
    )
    db.add(gatepass)
    db.commit()

    # Real-time notification for admins
    await manager.broadcast({
        "type": "new_request",
        "message": f"New Gate Pass Request from {student.name} (Roll {student.roll_number})",
        "student_name": student.name,
        "roll_number": student.roll_number,
    })

    return RedirectResponse(url="/student/dashboard", status_code=302)


@router.get("/pass/{pass_id}")
async def view_pass(pass_id: int, request: Request, db: Session = Depends(get_db)):
    student = get_student_from_token(request, db)
    if not student:
        return RedirectResponse(url="/auth/student/login")

    gatepass = (
        db.query(GatePass)
        .filter(GatePass.id == pass_id, GatePass.student_id == student.id)
        .first()
    )
    if not gatepass:
        return RedirectResponse(url="/student/dashboard")

    qr_data = None
    if gatepass.qr_token:
        verify_url = str(request.base_url) + f"verify/{gatepass.qr_token}"
        qr_data = generate_qr_code_base64(verify_url)

    return templates.TemplateResponse("student/gatepass_card.html", {
        "request": request,
        "student": student,
        "gatepass": gatepass,
        "qr_data": qr_data,
    })


@router.post("/cancel/{pass_id}")
async def cancel_pass(pass_id: int, request: Request, db: Session = Depends(get_db)):
    student = get_student_from_token(request, db)
    if not student:
        return RedirectResponse(url="/auth/student/login")

    gatepass = (
        db.query(GatePass)
        .filter(
            GatePass.id == pass_id,
            GatePass.student_id == student.id,
            GatePass.status == "Pending",
        )
        .first()
    )
    if gatepass:
        gatepass.status = "Cancelled"
        db.commit()

    if request.headers.get("HX-Request"):
        return HTMLResponse(
            '<span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-gray-100 text-gray-700">'
            "Cancelled</span>"
        )
    return RedirectResponse(url="/student/dashboard", status_code=302)


@router.get("/history")
async def history(request: Request, db: Session = Depends(get_db)):
    student = get_student_from_token(request, db)
    if not student:
        return RedirectResponse(url="/auth/student/login")

    passes = (
        db.query(GatePass)
        .filter(GatePass.student_id == student.id)
        .order_by(GatePass.created_at.desc())
        .all()
    )
    return templates.TemplateResponse("student/history.html", {
        "request": request,
        "student": student,
        "passes": passes,
    })


@router.get("/download/{pass_id}")
async def download_pdf(pass_id: int, request: Request, db: Session = Depends(get_db)):
    student = get_student_from_token(request, db)
    if not student:
        return RedirectResponse(url="/auth/student/login")

    gatepass = (
        db.query(GatePass)
        .filter(GatePass.id == pass_id, GatePass.student_id == student.id)
        .first()
    )
    if not gatepass:
        return RedirectResponse(url="/student/dashboard")

    approver_name = gatepass.approver.name if gatepass.approver else None
    base_url = str(request.base_url)
    pdf_buffer = generate_pass_pdf(gatepass, student, approver_name, base_url)

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=gatepass_{gatepass.id}.pdf"},
    )
