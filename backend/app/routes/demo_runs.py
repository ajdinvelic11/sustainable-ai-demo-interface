import asyncio
import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response, StreamingResponse

from app.auth.dependencies import require_admin, require_csrf, require_user
from app.config import Settings, get_settings
from app.db.session import db_connection
from app.schemas.auth import AuthUser
from app.schemas.demo import CurrentDemoResponse, DemoEvent, DemoRunState, DemoStartResponse, ResetStaleRequest, ResetStaleResponse
from app.services.certificate_service import CertificateError, CertificateService
from app.services.demo_orchestrator import DemoOrchestrator
from app.services.demo_repository import ACTIVE_RUN_STATUSES, DemoRepository, MigrationRequiredError


router = APIRouter(prefix="/api/demo-runs", tags=["demo-runs"])
_orchestrators: dict[int, DemoOrchestrator] = {}


def orchestrator(settings: Settings) -> DemoOrchestrator:
    key = id(settings)
    if key not in _orchestrators:
        _orchestrators[key] = DemoOrchestrator(settings)
    return _orchestrators[key]


def _state_for_run_id(settings: Settings, demo_run_id: int) -> DemoRunState:
    with db_connection() as conn:
        repo = DemoRepository(conn, settings)
        repo.ensure_ui_tables()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM ml_ops.demo_ui_runs WHERE demo_run_id = %s", (demo_run_id,))
            run = cur.fetchone()
        if not run:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demo run not found.")
        return repo.build_state(run)


@router.post("/start", response_model=DemoStartResponse, dependencies=[Depends(require_csrf)])
async def start_demo_run(
    settings: Annotated[Settings, Depends(get_settings)],
    user: Annotated[AuthUser, Depends(require_user)],
) -> DemoStartResponse:
    demo_run_id = await orchestrator(settings).start_demo(user)
    return DemoStartResponse(demo_run_id=demo_run_id, status="STARTING")


@router.get("/current", response_model=CurrentDemoResponse)
def current_demo_run(
    settings: Annotated[Settings, Depends(get_settings)],
    _: Annotated[AuthUser, Depends(require_user)],
) -> CurrentDemoResponse:
    with db_connection() as conn:
        repo = DemoRepository(conn, settings)
        if not repo.ui_tables_available():
            return CurrentDemoResponse(active=False, latest=None, migration_required=True)
        active = repo.active_demo_run()
        latest = active or repo.latest_demo_run()
        return CurrentDemoResponse(
            active=bool(active),
            latest=repo.build_state(latest) if latest else None,
            migration_required=False,
        )


@router.get("/stream")
async def stream_demo_runs(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    _: Annotated[AuthUser, Depends(require_user)],
):
    async def event_generator():
        while not await request.is_disconnected():
            try:
                with db_connection() as conn:
                    repo = DemoRepository(conn, settings)
                    if not repo.ui_tables_available():
                        payload = {"migration_required": True, "active": False, "latest": None}
                    else:
                        active = repo.active_demo_run()
                        latest = active or repo.latest_demo_run()
                        payload = {
                            "migration_required": False,
                            "active": bool(active),
                            "latest": repo.build_state(latest).model_dump(mode="json") if latest else None,
                        }
                yield f"event: state\ndata: {json.dumps(payload)}\n\n"
            except Exception as exc:
                yield f"event: error\ndata: {json.dumps({'message': str(exc)})}\n\n"
            await asyncio.sleep(settings.demo_stream_interval_seconds)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/reset-stale", response_model=ResetStaleResponse, dependencies=[Depends(require_csrf)])
def reset_stale(
    payload: ResetStaleRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    user: Annotated[AuthUser, Depends(require_admin)],
) -> ResetStaleResponse:
    if not payload.confirm:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reset requires confirm=true.")
    with db_connection() as conn:
        repo = DemoRepository(conn, settings)
        try:
            reset_runs, reset_commands = repo.reset_stale(payload.fail_open_commands)
            latest = repo.latest_demo_run()
            if latest:
                repo.add_event(
                    int(latest["demo_run_id"]),
                    "STALE_STATE_RESET",
                    f"Stale demo state reset by {user.subject}.",
                    severity="WARN",
                    metadata={"reset_runs": reset_runs, "reset_commands": reset_commands},
                )
            conn.commit()
        except MigrationRequiredError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return ResetStaleResponse(reset_runs=reset_runs, reset_commands=reset_commands)


@router.get("/{demo_run_id}", response_model=DemoRunState)
def get_demo_run(
    demo_run_id: int,
    settings: Annotated[Settings, Depends(get_settings)],
    _: Annotated[AuthUser, Depends(require_user)],
) -> DemoRunState:
    try:
        return _state_for_run_id(settings, demo_run_id)
    except MigrationRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.get("/{demo_run_id}/events", response_model=list[DemoEvent])
def get_demo_events(
    demo_run_id: int,
    settings: Annotated[Settings, Depends(get_settings)],
    _: Annotated[AuthUser, Depends(require_user)],
) -> list[DemoEvent]:
    with db_connection() as conn:
        repo = DemoRepository(conn, settings)
        try:
            events = repo.list_events(demo_run_id)
        except MigrationRequiredError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
        return [DemoEvent(**event) for event in events]


@router.get("/{demo_run_id}/certificate")
def export_demo_certificate(
    demo_run_id: int,
    settings: Annotated[Settings, Depends(get_settings)],
    _: Annotated[AuthUser, Depends(require_user)],
) -> Response:
    with db_connection() as conn:
        service = CertificateService(conn, settings)
        try:
            certificate = service.generate_certificate(demo_run_id)
        except MigrationRequiredError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
        except CertificateError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    filename = f"sustainable-ai-training-certificate-{demo_run_id}.json"
    return Response(
        content=service.to_pretty_json(certificate),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
