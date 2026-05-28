from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SiteInfo(BaseModel):
    location_name: str
    region_code: str
    host: str | None = None
    role: str | None = None
    current_status: str | None = None
    last_seen_at: datetime | None = None


class DemoEvent(BaseModel):
    event_id: int | None = None
    demo_run_id: int
    event_type: str
    severity: str = "INFO"
    message: str
    location_name: str | None = None
    region_code: str | None = None
    phase_no: int | None = None
    command_id: int | None = None
    training_run_id: int | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime


class DemoPhase(BaseModel):
    phase_no: int
    location_name: str
    region_code: str
    target_percent: int
    target_duration_seconds: int
    status: str = "PENDING"
    command_id: int | None = None
    command_status: str | None = None
    training_run_id: int | None = None
    output_checkpoint_s3_uri: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class LiveMetrics(BaseModel):
    command_id: int | None = None
    training_run_id: int | None = None
    current_status: str | None = None
    progress_percent: float | None = None
    epoch: int | None = None
    total_epochs: int | None = None
    map50: float | None = Field(default=None, alias="mAP50")
    precision: float | None = None
    recall: float | None = None
    message: str | None = None
    updated_at: datetime | None = None

    class Config:
        populate_by_name = True


class CurrentPhase(BaseModel):
    phase_no: int
    location_name: str
    region_code: str
    target_percent: int
    status: str
    command_id: int | None = None
    training_run_id: int | None = None


class FinalResult(BaseModel):
    final_training_run_id: int | None = None
    final_checkpoint_s3_uri: str | None = None
    best_model_s3_uri: str | None = None


class DemoState(BaseModel):
    demo_run_id: int | None = None
    demo_name: str | None = None
    status: str = "NOT_STARTED"
    setup_required: bool = False
    warning: str | None = None
    overall_progress_percent: float = 0
    current_phase: CurrentPhase | None = None
    phases: list[DemoPhase] = []
    latest_metrics: LiveMetrics | None = None
    latest_checkpoint_s3_uri: str | None = None
    final_result: FinalResult = Field(default_factory=FinalResult)
    events: list[DemoEvent] = []
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    updated_at: datetime | None = None


class StartDemoResponse(BaseModel):
    demo_run_id: int
    status: str
    message: str


class ResetStaleRequest(BaseModel):
    confirm: bool = False
    mark_open_commands_failed: bool = False
    reason: str | None = None


class ResetStaleResponse(BaseModel):
    reset_demo_runs: int
    reset_commands: int
    message: str


class ConflictDetail(BaseModel):
    active_demo_run_id: int | None = None
    open_commands: list[dict[str, Any]] = []
    message: str

