"""
GhostExodus OSINT Platform — FastAPI Entry Point
"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from config import settings
from database import create_db_and_tables, get_session, User, user_count, write_audit_log
from auth.utils import hash_password

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ghostexodus")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info("GhostExodus OSINT Platform starting...")

    # Initialise DB
    create_db_and_tables()
    logger.info("Database tables verified")

    # Start Telegram monitors
    try:
        from collector.channel_monitor import start_all_monitors
        await start_all_monitors()
    except Exception as e:
        logger.warning(f"Telegram monitor startup failed (will retry when channels added): {e}")

    # Start APScheduler
    from collector.scheduler import start_scheduler
    start_scheduler()

    logger.info("GhostExodus ready")
    yield

    # Shutdown
    logger.info("GhostExodus shutting down...")
    from collector.scheduler import stop_scheduler
    stop_scheduler()
    try:
        from collector.telegram_client import disconnect_client
        await disconnect_client()
    except Exception:
        pass
    logger.info("Shutdown complete")


app = FastAPI(
    title="GhostExodus OSINT Platform",
    version="1.0.0",
    description="Counter-extremism intelligence monitoring platform",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ─── CORS (dev only) ──────────────────────────────────────────────────────────
if settings.ENV == "development":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.FRONTEND_DEV_ORIGIN],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# ─── Routers ─────────────────────────────────────────────────────────────────
from auth.router import router as auth_router
from routers.feed import router as feed_router
from routers.search import router as search_router
from routers.entities import router as entities_router
from routers.timeline import router as timeline_router
from routers.alerts import router as alerts_router
from routers.reports import router as reports_router
from routers.evidence import router as evidence_router
from routers.channels import router as channels_router
from routers.admin import router as admin_router

app.include_router(auth_router)
app.include_router(feed_router)
app.include_router(search_router)
app.include_router(entities_router)
app.include_router(timeline_router)
app.include_router(alerts_router)
app.include_router(reports_router)
app.include_router(evidence_router)
app.include_router(channels_router)
app.include_router(admin_router)


# ─── First-run setup endpoint ────────────────────────────────────────────────
from pydantic import BaseModel as PydanticBase

class SetupRequest(PydanticBase):
    username: str
    password: str


@app.get("/api/setup/status")
async def setup_status():
    from sqlmodel import Session
    with Session(__import__("database", fromlist=["engine"]).engine) as session:
        count = user_count(session)
    return {"setup_required": count == 0}


@app.post("/api/setup/init")
async def setup_init(payload: SetupRequest):
    from sqlmodel import Session
    with Session(__import__("database", fromlist=["engine"]).engine) as session:
        count = user_count(session)
        if count > 0:
            return JSONResponse(status_code=403, content={"detail": "Setup already completed"})

        if len(payload.password) < 8:
            return JSONResponse(status_code=400, content={"detail": "Password must be at least 8 characters"})

        user = User(
            username=payload.username,
            password_hash=hash_password(payload.password),
            role="ADMIN",
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        write_audit_log(
            session,
            action="INITIAL_ADMIN_CREATED",
            user_id=user.id,
            detail={"username": payload.username},
        )

    logger.info(f"Initial admin account created: {payload.username}")
    return {"status": "setup_complete", "username": payload.username, "role": "ADMIN"}


# ─── Serve frontend static files ─────────────────────────────────────────────
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    # Serve built React app — all non-API routes → index.html (SPA)
    app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        from fastapi.responses import FileResponse
        index = os.path.join(static_dir, "index.html")
        if os.path.exists(index):
            return FileResponse(index)
        return JSONResponse(status_code=404, content={"detail": "Frontend not built yet"})
else:
    @app.get("/")
    async def root():
        return {
            "status": "running",
            "message": "GhostExodus API is running. Frontend not yet built.",
            "docs": "/api/docs",
        }
