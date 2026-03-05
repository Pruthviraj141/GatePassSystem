"""
Verification route — public QR-code verification endpoint.
"""

from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import GatePass

router = APIRouter(tags=["verify"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/verify/{token}")
async def verify_pass(token: str, request: Request, db: Session = Depends(get_db)):
    gatepass = db.query(GatePass).filter(GatePass.qr_token == token).first()

    if not gatepass:
        return templates.TemplateResponse("verify/verify_pass.html", {
            "request": request,
            "valid": False,
            "status": "INVALID PASS",
            "gatepass": None,
        })

    is_valid = gatepass.status == "Approved"
    if gatepass.status == "Expired":
        status_label = "EXPIRED PASS"
    elif is_valid:
        status_label = "VALID PASS"
    else:
        status_label = "INVALID PASS"

    return templates.TemplateResponse("verify/verify_pass.html", {
        "request": request,
        "valid": is_valid,
        "status": status_label,
        "gatepass": gatepass,
    })
