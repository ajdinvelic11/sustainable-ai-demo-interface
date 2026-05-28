from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.auth.session import require_admin
from app.routes.dependencies import get_current_user, get_orchestrator, get_settings_from_app
from app.schemas.auth import SessionUser
from app.schemas.demo import DemoEvent, DemoState, ResetStaleRequest, ResetStaleResponse, SiteInfo, StartDemoResponse
from app.services.demo_orchestrator import DemoOrchestrator
from app.services.demo_repository import ActiveDemoConflict, MissingDemoTablesError

router = APIRouter(prefix="/api", tags=["demo"])


@router.post("/demo-runs/start", response_model=StartDemoResponse)
def start_demo_run(
    user: SessionUser = Depends(get_current_user),
    orchestrator: DemoOrchestrator = Depends(get_orchestrator),
) -> StartDemoResponse:
    try:
        demo_run_id = orchestrator.start_demo(user)
    except MissingDemoTablesError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except ActiveDemoConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": str(exc),
                "active_demo_run_id": exc.active_demo_run_id,
                "open_commands": exc.open_commands,
            },
        ) from exc
    return StartDemoResponse(
        demo_run_id=demo_run_id,
        status="STARTING",
        message="Demo run started.",
    )


@router.get("/demo-runs/current", response_model=DemoState)
def current_demo_run(
    user: SessionUser = Depends(get_current_user),
    orchestrator: DemoOrchestrator = Depends(get_orchestrator),
) -> DemoState:
    return orchestrator.current_state()


@router.get("/demo-runs/stream")
async def stream_demo_runs(
    user: SessionUser = Depends(get_current_user),
    orchestrator: DemoOrchestrator = Depends(get_orchestrator),
    settings=Depends(get_settings_from_app),
) -> StreamingResponse:
    async def event_generator() -> AsyncIterator[str]:
        while True:
            state = await asyncio.to_thread(orchestrator.current_state)
            payload = state.model_dump(mode="json", by_alias=True)
            yield f"event: demo-state\ndata: {json.dumps(payload)}\n\n"
            await asyncio.sleep(settings.demo_stream_interval_seconds)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/demo-runs/{demo_run_id}", response_model=DemoState)
def demo_run_details(
    demo_run_id: int,
    user: SessionUser = Depends(get_current_user),
    orchestrator: DemoOrchestrator = Depends(get_orchestrator),
) -> DemoState:
    return orchestrator.state_for_run(demo_run_id)


@router.get("/demo-runs/{demo_run_id}/events", response_model=list[DemoEvent])
def demo_run_events(
    demo_run_id: int,
    user: SessionUser = Depends(get_current_user),
    orchestrator: DemoOrchestrator = Depends(get_orchestrator),
) -> list[DemoEvent]:
    return orchestrator.repository.events_for_run(demo_run_id)


@router.post("/demo-runs/reset-stale", response_model=ResetStaleResponse)
def reset_stale(
    payload: ResetStaleRequest,
    user: SessionUser = Depends(get_current_user),
    orchestrator: DemoOrchestrator = Depends(get_orchestrator),
) -> ResetStaleResponse:
    require_admin(user)
    if not payload.confirm:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Confirmation is required.")
    try:
        reset_runs, reset_commands = orchestrator.repository.reset_stale(
            user,
            mark_open_commands_failed=payload.mark_open_commands_failed,
            reason=payload.reason,
        )
    except MissingDemoTablesError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return ResetStaleResponse(
        reset_demo_runs=reset_runs,
        reset_commands=reset_commands,
        message="Stale demo state was marked failed.",
    )


@router.get("/system/sites", response_model=list[SiteInfo])
def system_sites(user: SessionUser = Depends(get_current_user), settings=Depends(get_settings_from_app)) -> list[SiteInfo]:
    return [
        SiteInfo(
            location_name=settings.site_wiener_neustadt_location_name,
            region_code=settings.site_wiener_neustadt_region_code,
            host="ec2-wiener-neustadt",
            role="existing central/cloud training site",
        ),
        SiteInfo(
            location_name=settings.site_wien_location_name,
            region_code=settings.site_wien_region_code,
            host="cloud-pi-wien",
            role="temporary cloud replacement for Raspberry Pi Wien",
        ),
        SiteInfo(
            location_name=settings.site_eisenstadt_location_name,
            region_code=settings.site_eisenstadt_region_code,
            host="cloud-pi-eisenstadt",
            role="temporary cloud replacement for Raspberry Pi Eisenstadt",
        ),
    ]

