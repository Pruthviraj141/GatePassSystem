"""
Admin routes — dashboard, request management, admin CRUD.
"""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import GatePass, Admin
from app.auth import get_admin_from_token, hash_password
from app.services.qr_service import generate_qr_token
from app.services.gatepass_service import get_pass_counts

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")


# ─── Dashboard ────────────────────────────────────────────────────────────────

@router.get("/dashboard")
async def dashboard(request: Request, db: Session = Depends(get_db)):
    admin = get_admin_from_token(request, db)
    if not admin:
        return RedirectResponse(url="/auth/admin/login")

    counts = get_pass_counts(db)
    recent_pending = (
        db.query(GatePass)
        .options(joinedload(GatePass.student))
        .filter(GatePass.status == "Pending")
        .order_by(GatePass.created_at.desc())
        .limit(5)
        .all()
    )
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "admin": admin,
        "counts": counts,
        "recent_pending": recent_pending,
    })


# ─── Requests ─────────────────────────────────────────────────────────────────

@router.get("/requests")
async def all_requests(
    request: Request,
    status: str = None,
    db: Session = Depends(get_db),
):
    admin = get_admin_from_token(request, db)
    if not admin:
        return RedirectResponse(url="/auth/admin/login")

    query = db.query(GatePass).options(joinedload(GatePass.student))
    if status and status != "all":
        query = query.filter(GatePass.status == status)
    passes = query.order_by(GatePass.created_at.desc()).all()
    counts = get_pass_counts(db)

    return templates.TemplateResponse("admin/requests.html", {
        "request": request,
        "admin": admin,
        "passes": passes,
        "current_filter": status or "all",
        "counts": counts,
    })


# ─── Approve / Reject (HTMX) ─────────────────────────────────────────────────

@router.post("/approve/{pass_id}")
async def approve_pass(pass_id: int, request: Request, db: Session = Depends(get_db)):
    admin = get_admin_from_token(request, db)
    if not admin:
        return RedirectResponse(url="/auth/admin/login")

    gatepass = db.query(GatePass).filter(GatePass.id == pass_id, GatePass.status == "Pending").first()
    if gatepass:
        gatepass.status = "Approved"
        gatepass.approved_by = admin.id
        gatepass.qr_token = generate_qr_token()
        db.commit()
        db.refresh(gatepass)

    if request.headers.get("HX-Request") and gatepass:
        return HTMLResponse(f'''
        <div id="pass-card-{pass_id}"
             class="bg-white rounded-2xl shadow-lg border border-emerald-200 p-5 transition-all">
            <div class="flex items-center justify-between mb-3">
                <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-700">
                    ✓ Approved
                </span>
                <span class="text-xs text-slate-400 font-mono">#{pass_id:04d}</span>
            </div>
            <p class="text-sm text-slate-600">
                <span class="font-semibold text-slate-800">{gatepass.student.name}</span>
                <span class="text-slate-400 mx-1">·</span>
                {gatepass.student.roll_number}
            </p>
            <p class="text-xs text-slate-500 mt-1">{gatepass.reason[:50]}</p>
            <p class="text-xs text-emerald-600 mt-2 font-medium">Approved by {admin.name}</p>
        </div>''')

    return RedirectResponse(url="/admin/requests", status_code=302)


@router.post("/reject/{pass_id}")
async def reject_pass(pass_id: int, request: Request, db: Session = Depends(get_db)):
    admin = get_admin_from_token(request, db)
    if not admin:
        return RedirectResponse(url="/auth/admin/login")

    gatepass = db.query(GatePass).filter(GatePass.id == pass_id, GatePass.status == "Pending").first()
    if gatepass:
        gatepass.status = "Rejected"
        gatepass.approved_by = admin.id
        db.commit()
        db.refresh(gatepass)

    if request.headers.get("HX-Request") and gatepass:
        return HTMLResponse(f'''
        <div id="pass-card-{pass_id}"
             class="bg-white rounded-2xl shadow-lg border border-red-200 p-5 transition-all">
            <div class="flex items-center justify-between mb-3">
                <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-red-100 text-red-700">
                    ✗ Rejected
                </span>
                <span class="text-xs text-slate-400 font-mono">#{pass_id:04d}</span>
            </div>
            <p class="text-sm text-slate-600">
                <span class="font-semibold text-slate-800">{gatepass.student.name}</span>
                <span class="text-slate-400 mx-1">·</span>
                {gatepass.student.roll_number}
            </p>
            <p class="text-xs text-slate-500 mt-1">{gatepass.reason[:50]}</p>
            <p class="text-xs text-red-600 mt-2 font-medium">Rejected by {admin.name}</p>
        </div>''')

    return RedirectResponse(url="/admin/requests", status_code=302)


# ─── Admin Management ─────────────────────────────────────────────────────────

@router.get("/admins")
async def admin_management(request: Request, db: Session = Depends(get_db)):
    admin = get_admin_from_token(request, db)
    if not admin:
        return RedirectResponse(url="/auth/admin/login")

    admins = db.query(Admin).order_by(Admin.created_at.desc()).all()
    return templates.TemplateResponse("admin/admins.html", {
        "request": request,
        "admin": admin,
        "admins": admins,
    })


@router.post("/admins/create")
async def create_admin(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    admin = get_admin_from_token(request, db)
    if not admin:
        return RedirectResponse(url="/auth/admin/login")

    if db.query(Admin).filter(Admin.email == email).first():
        admins = db.query(Admin).order_by(Admin.created_at.desc()).all()
        return templates.TemplateResponse("admin/admins.html", {
            "request": request,
            "admin": admin,
            "admins": admins,
            "error": "Email already registered",
        })

    new_admin = Admin(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role="admin",
    )
    db.add(new_admin)
    db.commit()
    return RedirectResponse(url="/admin/admins", status_code=302)


@router.post("/admins/delete/{admin_id}")
async def delete_admin(admin_id: int, request: Request, db: Session = Depends(get_db)):
    admin = get_admin_from_token(request, db)
    if not admin:
        return RedirectResponse(url="/auth/admin/login")

    target = db.query(Admin).filter(Admin.id == admin_id).first()
    if target and target.id != admin.id and target.role != "superadmin":
        db.delete(target)
        db.commit()

    if request.headers.get("HX-Request"):
        return HTMLResponse("")
    return RedirectResponse(url="/admin/admins", status_code=302)
