"""
Campus GatePass System — FastAPI application entry point.

Handles:
  • Database & table creation on startup
  • Default admin seeding
  • Background auto-expiry of approved passes
  • Router registration
  • Static file serving
"""

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.database import engine, Base, SessionLocal
from app.models import Admin, GatePass
from app.auth import hash_password
from app.routes import (
    auth_routes,
    student_routes,
    admin_routes,
    verify_routes,
    websocket_routes,
)

# Thread pool for running sync DB calls without blocking the event loop
_db_executor = ThreadPoolExecutor(max_workers=2)


# ─── Background task ─────────────────────────────────────────────────────────

def _expire_passes_sync():
    """Synchronous helper — runs in a thread so the event loop stays free."""
    db = SessionLocal()
    try:
        now = datetime.now()
        approved = db.query(GatePass).filter(GatePass.status == "Approved").all()
        for gp in approved:
            try:
                pass_end = datetime.strptime(
                    f"{gp.date} {gp.return_time}", "%Y-%m-%d %H:%M"
                )
                if now > pass_end:
                    gp.status = "Expired"
            except ValueError:
                continue
        db.commit()
    except Exception as exc:
        print(f"[auto-expire] error: {exc}")
    finally:
        db.close()


async def auto_expire_passes():
    """Every 60 s, mark Approved passes whose return_time has passed as Expired."""
    loop = asyncio.get_running_loop()
    while True:
        await loop.run_in_executor(_db_executor, _expire_passes_sync)
        await asyncio.sleep(60)


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables
    Base.metadata.create_all(bind=engine)

    # Seed default super-admin from environment variables
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@123")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
    ADMIN_NAME = os.getenv("ADMIN_NAME", "Super Admin")

    db = SessionLocal()
    try:
        if not db.query(Admin).filter(Admin.email == ADMIN_EMAIL).first():
            db.add(
                Admin(
                    name=ADMIN_NAME,
                    email=ADMIN_EMAIL,
                    password_hash=hash_password(ADMIN_PASSWORD),
                    role="superadmin",
                )
            )
            db.commit()
            print(f"[startup] Default admin created — {ADMIN_EMAIL} / (hidden)")
    finally:
        db.close()

    # Background expiry checker
    task = asyncio.create_task(auto_expire_passes())
    yield
    task.cancel()


# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Campus GatePass System",
    version="1.0.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth_routes.router)
app.include_router(student_routes.router)
app.include_router(admin_routes.router)
app.include_router(verify_routes.router)
app.include_router(websocket_routes.router)


@app.get("/")
async def root():
    return RedirectResponse(url="/auth/student/login")
