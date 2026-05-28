from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.db.session import close_pool, db_connection, init_pool
from app.routes import auth, demo_runs, system
from app.services.demo_repository import DemoRepository
from app.utils.logging import configure_logging


settings = get_settings()
configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_pool()
    yield
    close_pool()


app = FastAPI(
    title="Sustainable AI Demo Interface API",
    version="1.0.0",
    description="Control-plane API for the Sustainable AI multi-site training demo.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins or [settings.app_public_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(demo_runs.router)
app.include_router(system.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready(settings: Annotated[Settings, Depends(get_settings)]) -> dict[str, object]:
    db_ok = False
    migrations_ok = False
    try:
        with db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 AS ok")
                db_ok = cur.fetchone()["ok"] == 1
            repo = DemoRepository(conn, settings)
            migrations_ok = repo.ui_tables_available()
    except Exception:
        db_ok = False
    return {"status": "ready" if db_ok else "not-ready", "database": db_ok, "demo_ui_tables": migrations_ok}
