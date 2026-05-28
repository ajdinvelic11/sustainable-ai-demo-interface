from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any

from app.config import Settings
from app.db import Database
from app.schemas.auth import SessionUser
from app.schemas.demo import DemoState
from app.services.demo_repository import (
    ActiveDemoConflict,
    COMPLETED_COMMAND_STATUSES,
    FAILED_COMMAND_STATUSES,
    OPEN_COMMAND_STATUSES,
    DemoRepository,
    MissingDemoTablesError,
    utc_now,
)

logger = logging.getLogger(__name__)


class DemoOrchestrator:
    def __init__(self, db: Database, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.repository = DemoRepository(db, settings)
        self._threads: dict[int, threading.Thread] = {}
        self._lock = threading.Lock()

    def start_demo(self, user: SessionUser) -> int:
        demo_run_id = self.repository.create_demo(user)
        self._start_thread(demo_run_id)
        return demo_run_id

    def resume_active_runs(self) -> None:
        try:
            state = self.repository.latest_run_state(include_events=False)
        except Exception as exc:
            logger.warning("resume_active_runs_failed", extra={"_error": str(exc)})
            return
        if state.demo_run_id and state.status in {"STARTING", "RUNNING"}:
            self._start_thread(state.demo_run_id)

    def _start_thread(self, demo_run_id: int) -> None:
        with self._lock:
            existing = self._threads.get(demo_run_id)
            if existing and existing.is_alive():
                return
            thread = threading.Thread(
                target=self._orchestrate_safely,
                args=(demo_run_id,),
                name=f"demo-orchestrator-{demo_run_id}",
                daemon=True,
            )
            self._threads[demo_run_id] = thread
            thread.start()

    def _orchestrate_safely(self, demo_run_id: int) -> None:
        try:
            self._orchestrate(demo_run_id)
        except Exception as exc:
            logger.exception("demo_orchestration_failed", extra={"_demo_run_id": demo_run_id})
            self._mark_failed(demo_run_id, str(exc))

    def _orchestrate(self, demo_run_id: int) -> None:
        previous_checkpoint: str | None = None
        final_training_run_id: int | None = None
        chain_test_id: int | None = None
        with self.db.connection() as conn:
            row = conn.execute("select * from ml_ops.demo_ui_runs where demo_run_id = %s", (demo_run_id,)).fetchone()
            if not row:
                raise RuntimeError(f"Demo run {demo_run_id} no longer exists.")
            chain_test_id = row.get("linked_chain_test_id")
            self.repository.update_demo_run(conn, demo_run_id, {"status": "RUNNING"})

        for phase in self.settings.phase_plan:
            phase_started_at = time.monotonic()
            phase_no = int(phase["phase_no"])
            with self.db.connection() as conn:
                with conn.transaction():
                    self.repository.update_demo_run(
                        conn,
                        demo_run_id,
                        {
                            "status": "RUNNING",
                            "current_phase_no": phase_no,
                            "current_command_id": None,
                        },
                    )
                    self.repository.create_event(
                        conn,
                        demo_run_id=demo_run_id,
                        event_type="PHASE_STARTED",
                        message=f"Phase {phase_no} started for {phase['location_name']}.",
                        location_name=phase["location_name"],
                        region_code=phase["region_code"],
                        phase_no=phase_no,
                        metadata={
                            "target_percent": phase["target_percent"],
                            "target_duration_seconds": phase["target_duration_seconds"],
                            "resume_checkpoint_s3_uri": previous_checkpoint,
                        },
                    )
                    self.repository.create_chain_phase(conn, demo_run_id, chain_test_id, phase, previous_checkpoint)
                    command_id = self.repository.create_edge_command(conn, demo_run_id, chain_test_id, phase, previous_checkpoint)
                    self.repository.update_demo_run(conn, demo_run_id, {"current_command_id": command_id})

            command = self._wait_for_command_completion(demo_run_id, phase, command_id)
            final_training_run_id = self.repository.command_training_run_id(command) or final_training_run_id
            output_checkpoint = self.repository.command_checkpoint_uri(command)
            if output_checkpoint:
                previous_checkpoint = output_checkpoint

            with self.db.connection() as conn:
                with conn.transaction():
                    self.repository.create_event(
                        conn,
                        demo_run_id=demo_run_id,
                        event_type="PHASE_COMPLETED",
                        message=f"Phase {phase_no} completed at {phase['location_name']}.",
                        location_name=phase["location_name"],
                        region_code=phase["region_code"],
                        phase_no=phase_no,
                        command_id=command_id,
                        training_run_id=final_training_run_id,
                        metadata={"output_checkpoint_s3_uri": output_checkpoint},
                    )

            elapsed = time.monotonic() - phase_started_at
            remaining = int(phase["target_duration_seconds"] - elapsed)
            if self.settings.demo_enforce_phase_timing and remaining > 0:
                with self.db.connection() as conn:
                    self.repository.create_event(
                        conn,
                        demo_run_id=demo_run_id,
                        event_type="CHECKPOINT_TRANSFER_WINDOW",
                        message="Checkpoint validation and transfer window active before the next site.",
                        location_name=phase["location_name"],
                        region_code=phase["region_code"],
                        phase_no=phase_no,
                        command_id=command_id,
                        metadata={"remaining_seconds": remaining},
                    )
                time.sleep(remaining)

        with self.db.connection() as conn:
            with conn.transaction():
                self.repository.update_demo_run(
                    conn,
                    demo_run_id,
                    {
                        "status": "COMPLETED",
                        "current_phase_no": 4,
                        "final_training_run_id": final_training_run_id,
                        "final_checkpoint_s3_uri": previous_checkpoint,
                        "finished_at": utc_now(),
                    },
                )
                self.repository.create_event(
                    conn,
                    demo_run_id=demo_run_id,
                    event_type="DEMO_COMPLETED",
                    message="Demo completed successfully.",
                    training_run_id=final_training_run_id,
                    metadata={"final_checkpoint_s3_uri": previous_checkpoint},
                )

    def _wait_for_command_completion(self, demo_run_id: int, phase: dict[str, Any], command_id: int) -> dict[str, Any]:
        previous_status: str | None = None
        while True:
            command = self.repository.get_command(command_id)
            status = self.repository.command_status(command)
            if status and status != previous_status:
                self._record_status_transition(demo_run_id, phase, command_id, status, command)
                previous_status = status
            if status in COMPLETED_COMMAND_STATUSES:
                return command or {}
            if status in FAILED_COMMAND_STATUSES:
                with self.db.connection() as conn:
                    self.repository.create_event(
                        conn,
                        demo_run_id=demo_run_id,
                        event_type="PHASE_FAILED",
                        severity="ERROR",
                        message=f"Phase {phase['phase_no']} command failed with status {status}.",
                        location_name=phase["location_name"],
                        region_code=phase["region_code"],
                        phase_no=phase["phase_no"],
                        command_id=command_id,
                        metadata={"command_status": status},
                    )
                raise RuntimeError(f"Command {command_id} failed with status {status}.")
            time.sleep(self.settings.demo_command_poll_interval_seconds)

    def _record_status_transition(
        self,
        demo_run_id: int,
        phase: dict[str, Any],
        command_id: int,
        command_status: str,
        command: dict[str, Any] | None,
    ) -> None:
        event_type = "COMMAND_STATUS_CHANGED"
        message = f"Command status changed to {command_status}."
        if command_status == "PICKED_UP":
            event_type = "COMMAND_PICKED_UP"
            message = "Site edge agent picked up the command."
        elif command_status == "RUNNING":
            event_type = "TRAINING_STARTED"
            message = "Training container is running."
        elif command_status in COMPLETED_COMMAND_STATUSES:
            event_type = "CHECKPOINT_UPLOADED"
            message = "Training completed and checkpoint metadata is available."
        with self.db.connection() as conn:
            self.repository.create_event(
                conn,
                demo_run_id=demo_run_id,
                event_type=event_type,
                message=message,
                location_name=phase["location_name"],
                region_code=phase["region_code"],
                phase_no=phase["phase_no"],
                command_id=command_id,
                training_run_id=self.repository.command_training_run_id(command),
                metadata={
                    "command_status": command_status,
                    "output_checkpoint_s3_uri": self.repository.command_checkpoint_uri(command),
                },
            )

    def _mark_failed(self, demo_run_id: int, error_message: str) -> None:
        try:
            with self.db.connection() as conn:
                with conn.transaction():
                    self.repository.update_demo_run(
                        conn,
                        demo_run_id,
                        {
                            "status": "FAILED",
                            "error_message": error_message,
                            "finished_at": datetime.now(timezone.utc),
                        },
                    )
                    self.repository.create_event(
                        conn,
                        demo_run_id=demo_run_id,
                        event_type="DEMO_FAILED",
                        severity="ERROR",
                        message="Demo orchestration failed.",
                        metadata={"error": error_message},
                    )
        except Exception:
            logger.exception("failed_to_mark_demo_failed", extra={"_demo_run_id": demo_run_id})

    def current_state(self) -> DemoState:
        return self.repository.latest_run_state()

    def state_for_run(self, demo_run_id: int) -> DemoState:
        return self.repository.state_for_run(demo_run_id)

