import asyncio
import logging
import time
from dataclasses import asdict
from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.config import Settings
from app.db.session import db_connection
from app.schemas.auth import AuthUser
from app.services.demo_repository import (
    ACTIVE_RUN_STATUSES,
    DemoRepository,
    MigrationRequiredError,
    configured_sites,
    phase_plan,
)


logger = logging.getLogger(__name__)


class DemoOrchestrator:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._running_tasks: dict[int, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def start_demo(self, user: AuthUser) -> int:
        async with self._lock:
            with db_connection() as conn:
                repo = DemoRepository(conn, self.settings)
                try:
                    active = repo.active_demo_run()
                except MigrationRequiredError as exc:
                    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
                if active:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail={
                            "message": "A demo run is already active.",
                            "active_demo_run_id": active["demo_run_id"],
                            "open_command_count": 0,
                            "open_commands": [],
                        },
                    )
                open_commands = repo.open_edge_commands()
                if open_commands:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail={
                            "message": "Open edge training commands already exist. Reset stale demo state or wait for them to finish.",
                            "active_demo_run_id": None,
                            "open_command_count": len(open_commands),
                            "open_commands": open_commands,
                        },
                    )
                demo_run_id = repo.create_demo_run(started_by=user.subject, auth_subject=user.subject)
                linked_chain_test_id = repo.create_chain_test_if_possible(demo_run_id)
                repo.update_demo_run(demo_run_id, linked_chain_test_id=linked_chain_test_id, status="RUNNING")
                repo.add_event(
                    demo_run_id,
                    "CHAIN_TEST_LINKED" if linked_chain_test_id else "CHAIN_TEST_SKIPPED",
                    (
                        f"Linked manual chain test {linked_chain_test_id}."
                        if linked_chain_test_id
                        else "manual_training_chain_tests table unavailable or incompatible; continuing with UI run tables."
                    ),
                    metadata={"linked_chain_test_id": linked_chain_test_id},
                )
                conn.commit()

            task = asyncio.create_task(self._run_demo_background(demo_run_id))
            self._running_tasks[demo_run_id] = task
            task.add_done_callback(lambda _: self._running_tasks.pop(demo_run_id, None))
            return demo_run_id

    async def _run_demo_background(self, demo_run_id: int) -> None:
        await asyncio.to_thread(self._run_demo_sync, demo_run_id)

    def _run_demo_sync(self, demo_run_id: int) -> None:
        logger.info("Starting demo orchestration", extra={"demo_run_id": demo_run_id})
        previous_checkpoint: str | None = None
        final_training_run_id: int | None = None
        final_checkpoint: str | None = None
        try:
            with db_connection() as conn:
                repo = DemoRepository(conn, self.settings)
                run = self._get_run_or_fail(repo, demo_run_id)
                linked_chain_test_id = run.get("linked_chain_test_id")
                for plan in phase_plan(self.settings):
                    phase_started = time.monotonic()
                    repo.update_demo_run(
                        demo_run_id,
                        status="RUNNING",
                        current_phase_no=plan.phase_no,
                        current_command_id=None,
                    )
                    repo.upsert_chain_phase_if_possible(
                        linked_chain_test_id,
                        plan,
                        status="PENDING",
                        resume_checkpoint_s3_uri=previous_checkpoint,
                    )
                    repo.add_event(
                        demo_run_id,
                        "PHASE_CREATED",
                        f"Phase {plan.phase_no} created for {plan.location_name} ({plan.target_percent}%).",
                        location_name=plan.location_name,
                        region_code=plan.region_code,
                        phase_no=plan.phase_no,
                        metadata=asdict(plan) | {"resume_checkpoint_s3_uri": previous_checkpoint},
                    )
                    command_id = repo.insert_edge_command(demo_run_id, plan, previous_checkpoint)
                    repo.update_demo_run(demo_run_id, current_command_id=command_id)
                    repo.upsert_chain_phase_if_possible(
                        linked_chain_test_id,
                        plan,
                        status="PENDING",
                        command_id=command_id,
                        resume_checkpoint_s3_uri=previous_checkpoint,
                    )
                    repo.add_event(
                        demo_run_id,
                        "COMMAND_CREATED",
                        f"Training command {command_id} created for {plan.location_name}.",
                        location_name=plan.location_name,
                        region_code=plan.region_code,
                        phase_no=plan.phase_no,
                        command_id=command_id,
                        metadata={"resume_checkpoint_s3_uri": previous_checkpoint},
                    )
                    conn.commit()

                    training_run_id, output_checkpoint = self._poll_command_until_done(repo, demo_run_id, plan, command_id)
                    final_training_run_id = training_run_id or final_training_run_id
                    final_checkpoint = output_checkpoint or final_checkpoint
                    previous_checkpoint = output_checkpoint or previous_checkpoint

                    repo.upsert_chain_phase_if_possible(
                        linked_chain_test_id,
                        plan,
                        status="COMPLETED",
                        command_id=command_id,
                        training_run_id=training_run_id,
                        resume_checkpoint_s3_uri=previous_checkpoint,
                        output_checkpoint_s3_uri=output_checkpoint,
                    )
                    repo.add_event(
                        demo_run_id,
                        "PHASE_COMPLETED",
                        f"Phase {plan.phase_no} completed at {plan.location_name}.",
                        location_name=plan.location_name,
                        region_code=plan.region_code,
                        phase_no=plan.phase_no,
                        command_id=command_id,
                        training_run_id=training_run_id,
                        metadata={"output_checkpoint_s3_uri": output_checkpoint},
                    )
                    conn.commit()

                    elapsed = time.monotonic() - phase_started
                    remaining = plan.target_duration_seconds - elapsed
                    if self.settings.demo_enforce_phase_timing and remaining > 0:
                        repo.update_demo_run(demo_run_id, status="TRANSITION")
                        repo.add_event(
                            demo_run_id,
                            "CHECKPOINT_TRANSFER_WINDOW",
                            f"Checkpoint validation and transfer window for {round(remaining)} seconds.",
                            location_name=plan.location_name,
                            region_code=plan.region_code,
                            phase_no=plan.phase_no,
                            command_id=command_id,
                            metadata={"remaining_seconds": round(remaining, 2)},
                        )
                        conn.commit()
                        time.sleep(remaining)
                    if plan.phase_no < len(phase_plan(self.settings)):
                        repo.add_event(
                            demo_run_id,
                            "NEXT_SITE_SELECTED",
                            "Next training site selected.",
                            phase_no=plan.phase_no + 1,
                            metadata={"previous_checkpoint_s3_uri": previous_checkpoint},
                        )
                        conn.commit()

                repo.update_demo_run(
                    demo_run_id,
                    status="COMPLETED",
                    current_phase_no=4,
                    final_training_run_id=final_training_run_id,
                    final_checkpoint_s3_uri=final_checkpoint,
                    finished_at=datetime.now(timezone.utc),
                )
                repo.update_chain_test_if_possible(
                    linked_chain_test_id,
                    status="COMPLETED",
                    final_training_run_id=final_training_run_id,
                    final_checkpoint_s3_uri=final_checkpoint,
                )
                repo.add_event(
                    demo_run_id,
                    "DEMO_COMPLETED",
                    "Demo completed successfully.",
                    training_run_id=final_training_run_id,
                    metadata={"final_checkpoint_s3_uri": final_checkpoint},
                )
                conn.commit()
                logger.info("Demo orchestration completed", extra={"demo_run_id": demo_run_id})
        except Exception as exc:
            logger.exception("Demo orchestration failed", extra={"demo_run_id": demo_run_id})
            with db_connection() as conn:
                repo = DemoRepository(conn, self.settings)
                try:
                    run = self._get_run_or_fail(repo, demo_run_id)
                    repo.update_demo_run(
                        demo_run_id,
                        status="FAILED",
                        error_message=str(exc),
                        finished_at=datetime.now(timezone.utc),
                    )
                    repo.update_chain_test_if_possible(
                        run.get("linked_chain_test_id"),
                        status="FAILED",
                        error_message=str(exc),
                    )
                    repo.add_event(demo_run_id, "DEMO_FAILED", str(exc), severity="ERROR")
                    conn.commit()
                except Exception:
                    logger.exception("Failed to persist orchestration failure", extra={"demo_run_id": demo_run_id})

    def _poll_command_until_done(self, repo: DemoRepository, demo_run_id: int, plan, command_id: int) -> tuple[int | None, str | None]:
        seen_statuses: set[str] = set()
        while True:
            command = repo.get_command(command_id)
            command_status = repo.command_status(command)
            if command_status not in seen_statuses:
                seen_statuses.add(command_status)
                event_type = {
                    "PICKED_UP": "COMMAND_PICKED_UP",
                    "RUNNING": "TRAINING_STARTED",
                    "COMPLETED": "COMMAND_COMPLETED",
                    "FAILED": "PHASE_FAILED",
                }.get(command_status, "COMMAND_STATUS")
                repo.add_event(
                    demo_run_id,
                    event_type,
                    f"Command {command_id} status is {command_status}.",
                    severity="ERROR" if command_status == "FAILED" else "INFO",
                    location_name=plan.location_name,
                    region_code=plan.region_code,
                    phase_no=plan.phase_no,
                    command_id=command_id,
                    training_run_id=(command or {}).get("training_run_id"),
                )
                repo.conn.commit()

            if command_status == "COMPLETED":
                output_checkpoint = self._extract_checkpoint(command)
                training_run_id = (command or {}).get("training_run_id") or (command or {}).get("run_id")
                if output_checkpoint:
                    repo.add_event(
                        demo_run_id,
                        "CHECKPOINT_UPLOADED",
                        "Checkpoint URI detected for completed phase.",
                        location_name=plan.location_name,
                        region_code=plan.region_code,
                        phase_no=plan.phase_no,
                        command_id=command_id,
                        training_run_id=training_run_id,
                        metadata={"output_checkpoint_s3_uri": output_checkpoint},
                    )
                    repo.conn.commit()
                return training_run_id, output_checkpoint
            if command_status == "FAILED":
                raise RuntimeError(f"Training command {command_id} failed.")
            time.sleep(self.settings.demo_command_poll_interval_seconds)

    def _extract_checkpoint(self, command: dict | None) -> str | None:
        if not command:
            return None
        for key in ("output_checkpoint_s3_uri", "final_checkpoint_s3_uri", "checkpoint_s3_uri", "best_model_s3_uri"):
            value = command.get(key)
            if value:
                return str(value)
        for key in ("result_payload", "result", "metadata", "command_payload", "payload"):
            value = command.get(key)
            if isinstance(value, dict):
                for nested_key in ("output_checkpoint_s3_uri", "final_checkpoint_s3_uri", "checkpoint_s3_uri", "best_model_s3_uri"):
                    if value.get(nested_key):
                        return str(value[nested_key])
        return None

    def _get_run_or_fail(self, repo: DemoRepository, demo_run_id: int) -> dict:
        with repo.conn.cursor() as cur:
            cur.execute("SELECT * FROM ml_ops.demo_ui_runs WHERE demo_run_id = %s", (demo_run_id,))
            run = cur.fetchone()
        if not run:
            raise RuntimeError(f"Demo run {demo_run_id} not found.")
        return run
