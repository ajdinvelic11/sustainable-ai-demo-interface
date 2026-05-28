from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import Database
from app.routes import auth, demo
from app.services.demo_orchestrator import DemoOrchestrator
from app.utils.logging import configure_logging

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    db = Database(settings)
    db.open()
    orchestrator = DemoOrchestrator(db, settings)
    app.state.settings = settings
    app.state.db = db
    app.state.orchestrator = orchestrator
    if settings.vc_jwt_validation_mock_mode:
        logger.warning("demo_auth_mode_enabled")
    orchestrator.resume_active_runs()
    yield
    db.close()


app = FastAPI(
    title="Sustainable AI Demo Interface API",
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth.router)
app.include_router(demo.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict[str, object]:
    db: Database = app.state.db
    database_ok = db.ping()
    return {
        "status": "ready" if database_ok else "not_ready",
        "database": database_ok,
        "demo_ui_tables": db.relation_exists("ml_ops", "demo_ui_runs")
        and db.relation_exists("ml_ops", "demo_ui_events"),
    }

