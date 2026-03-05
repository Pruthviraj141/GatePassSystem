"""
Gate-pass business logic helpers.
"""

from sqlalchemy.orm import Session
from app.models import GatePass


def has_active_pass(db: Session, student_id: int) -> bool:
    """Return True if the student already has a Pending or Approved pass."""
    return (
        db.query(GatePass)
        .filter(
            GatePass.student_id == student_id,
            GatePass.status.in_(["Pending", "Approved"]),
        )
        .first()
        is not None
    )


def get_active_pass(db: Session, student_id: int):
    """Return the student's active pass (Pending or Approved), or None."""
    return (
        db.query(GatePass)
        .filter(
            GatePass.student_id == student_id,
            GatePass.status.in_(["Pending", "Approved"]),
        )
        .first()
    )


def get_pass_counts(db: Session) -> dict:
    """Return a dict with aggregate counts by status."""
    pending = db.query(GatePass).filter(GatePass.status == "Pending").count()
    approved = db.query(GatePass).filter(GatePass.status == "Approved").count()
    rejected = db.query(GatePass).filter(GatePass.status == "Rejected").count()
    expired = db.query(GatePass).filter(GatePass.status == "Expired").count()
    cancelled = db.query(GatePass).filter(GatePass.status == "Cancelled").count()
    return {
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
        "expired": expired,
        "cancelled": cancelled,
        "total": pending + approved + rejected + expired + cancelled,
    }
