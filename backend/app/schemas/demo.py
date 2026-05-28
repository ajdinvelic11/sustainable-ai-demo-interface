from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


RunStatus = Literal["STARTING", "RUNNING", "TRANSITION", "COMPLETED", "FAILED"]
CommandStatus = Literal["PENDING", "PICKED_UP", "RUNNING", "COMPLETED", "FAILED", "UNKNOWN"]


class SiteInfo(BaseModel):
    location_name: str
    region_code: str
    host_label: str
    role: str
    status: str = "configured"


class DemoStartResponse(BaseModel):
    demo_run_id: int
    status: str


class ResetStaleRequest(BaseModel):
    confirm: bool
    fail_open_commands: bool = False


class ResetStaleResponse(BaseModel):
    reset_runs: int
    reset_commands: int


class DemoEvent(BaseModel):
    event_id: int
    demo_run_id: int
    event_type: str
    severity: str
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
    status: str
    command_id: int | None = None
    command_status: str | None = None
    training_run_id: int | None = None
    resume_checkpoint_s3_uri: str | None = None
    output_checkpoint_s3_uri: str | None = None


class LiveMetrics(BaseModel):
    command_id: int | None = None
    training_run_id: int | None = None
    current_status: str | None = None
    progress_percent: float | None = None
    epoch: int | None = None
    total_epochs: int | None = None
    map50: float | None = None
    precision: float | None = None
    recall: float | None = None
    message: str | None = None
    updated_at: datetime | None = None


class FinalResult(BaseModel):
    final_training_run_id: int | None = None
    final_checkpoint_s3_uri: str | None = None
    s3_best_model_uri: str | None = None


class DemoRunState(BaseModel):
    demo_run_id: int
    demo_name: str
    status: str
    overall_progress_percent: float
    requested_duration_seconds: int
    started_by: str | None = None
    auth_subject: str | None = None
    current_phase: DemoPhase | None = None
    phases: list[DemoPhase]
    latest_metrics: LiveMetrics | None = None
    final_result: FinalResult
    events: list[DemoEvent]
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    updated_at: datetime


class CurrentDemoResponse(BaseModel):
    active: bool
    latest: DemoRunState | None = None
    migration_required: bool = False


class ConflictDetail(BaseModel):
    message: str
    active_demo_run_id: int | None = None
    open_command_count: int = 0
    open_commands: list[dict[str, Any]] = []
