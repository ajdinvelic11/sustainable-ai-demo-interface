from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from psycopg import Connection, sql
from psycopg.types.json import Jsonb

from app.config import Settings
from app.db import Database
from app.schemas.auth import SessionUser
from app.schemas.demo import CurrentPhase, DemoEvent, DemoPhase, DemoState, FinalResult, LiveMetrics

logger = logging.getLogger(__name__)

ACTIVE_RUN_STATUSES = ("STARTING", "RUNNING", "RESETTING")
OPEN_COMMAND_STATUSES = ("PENDING", "PICKED_UP", "RUNNING")
COMPLETED_COMMAND_STATUSES = ("COMPLETED", "SUCCEEDED", "SUCCESS", "DONE")
FAILED_COMMAND_STATUSES = ("FAILED", "ERROR", "CANCELLED", "CANCELED")


class MissingDemoTablesError(RuntimeError):
    pass


class ActiveDemoConflict(RuntimeError):
    def __init__(
        self,
        message: str,
        active_demo_run_id: int | None = None,
        open_commands: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.active_demo_run_id = active_demo_run_id
        self.open_commands = open_commands or []


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_status(value: Any) -> str | None:
    if value is None:
        return None
    return str(value).upper()


def first_value(row: dict[str, Any] | None, candidates: list[str]) -> Any:
    if not row:
        return None
    for key in candidates:
        if key in row and row[key] is not None:
            return row[key]
    return None


def as_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def maybe_json_value(columns: dict[str, dict[str, Any]], column: str, value: dict[str, Any]) -> Any:
    column_info = columns.get(column) or {}
    if column_info.get("udt_name") in {"json", "jsonb"} or column_info.get("data_type") in {"json", "jsonb"}:
        return Jsonb(value)
    return json.dumps(value)


class DemoRepository:
    def __init__(self, db: Database, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    def ui_tables_ready(self) -> bool:
        return self.db.relation_exists("ml_ops", "demo_ui_runs") and self.db.relation_exists("ml_ops", "demo_ui_events")

    def require_ui_tables(self) -> None:
        if not self.ui_tables_ready():
            raise MissingDemoTablesError(
                "Demo UI tables are missing. Run backend/sql migrations before starting a demo."
            )

    def create_demo(self, user: SessionUser) -> int:
        self.require_ui_tables()
        with self.db.connection() as conn:
            with conn.transaction():
                conn.execute("select pg_advisory_xact_lock(hashtext('sustainable-ai-demo-interface:start'))")
                active = self._find_active_run(conn)
                open_commands = self.get_open_commands(conn)
                if active or open_commands:
                    raise ActiveDemoConflict(
                        "A demo run or edge training command is already active.",
                        active_demo_run_id=as_int(active.get("demo_run_id")) if active else None,
                        open_commands=open_commands,
                    )

                row = self.db.insert_dynamic(
                    conn,
                    "ml_ops",
                    "demo_ui_runs",
                    {
                        "demo_name": "Sustainable AI 5-minute multi-site training demo",
                        "status": "STARTING",
                        "requested_duration_seconds": self.settings.demo_total_duration_seconds,
                        "started_by": user.email or user.name or user.subject,
                        "auth_subject": user.subject,
                        "started_at": utc_now(),
                        "updated_at": utc_now(),
                    },
                    returning_candidates=["demo_run_id", "id"],
                )
                demo_run_id = as_int(first_value(row, ["demo_run_id", "id"]))
                if demo_run_id is None:
                    raise RuntimeError("Could not determine demo_run_id after insert.")

                self.create_event(
                    conn,
                    demo_run_id=demo_run_id,
                    event_type="DEMO_STARTED",
                    message="Demo run requested from the web interface.",
                    metadata={"requested_by": user.subject, "auth_mode": user.auth_mode},
                )

                chain_test_id = self.create_chain_test(conn, demo_run_id, user)
                if chain_test_id:
                    self.update_demo_run(conn, demo_run_id, {"linked_chain_test_id": chain_test_id})
                return demo_run_id

    def _find_active_run(self, conn: Connection[Any]) -> dict[str, Any] | None:
        row = conn.execute(
            """
            select *
            from ml_ops.demo_ui_runs
            where status = any(%s)
            order by created_at desc
            limit 1
            """,
            (list(ACTIVE_RUN_STATUSES),),
        ).fetchone()
        return dict(row) if row else None

    def create_chain_test(self, conn: Connection[Any], demo_run_id: int, user: SessionUser) -> int | None:
        if not self.db.relation_exists("ml_ops", "manual_training_chain_tests"):
            self.create_event(
                conn,
                demo_run_id=demo_run_id,
                event_type="CHAIN_TEST_SKIPPED",
                severity="WARN",
                message="manual_training_chain_tests table was not found; using demo UI tables only.",
            )
            return None
        try:
            row = self.db.insert_dynamic(
                conn,
                "ml_ops",
                "manual_training_chain_tests",
                {
                    "demo_run_id": demo_run_id,
                    "demo_name": "Sustainable AI 5-minute demo",
                    "test_name": "Sustainable AI 5-minute demo",
                    "status": "STARTING",
                    "model_id": self.settings.demo_model_id,
                    "model_version": self.settings.demo_model_version,
                    "total_duration_seconds": self.settings.demo_total_duration_seconds,
                    "requested_duration_seconds": self.settings.demo_total_duration_seconds,
                    "started_by": user.email or user.name or user.subject,
                    "auth_subject": user.subject,
                    "created_at": utc_now(),
                    "started_at": utc_now(),
                    "updated_at": utc_now(),
                },
                returning_candidates=["chain_test_id", "manual_training_chain_test_id", "test_id", "id"],
            )
            chain_test_id = as_int(first_value(row, ["chain_test_id", "manual_training_chain_test_id", "test_id", "id"]))
            self.create_event(
                conn,
                demo_run_id=demo_run_id,
                event_type="CHAIN_TEST_CREATED",
                message="Linked manual training chain test record created.",
                metadata={"chain_test_id": chain_test_id},
            )
            return chain_test_id
        except Exception as exc:
            logger.warning("chain_test_insert_failed", extra={"_error": str(exc)})
            self.create_event(
                conn,
                demo_run_id=demo_run_id,
                event_type="CHAIN_TEST_COMPATIBILITY_WARNING",
                severity="WARN",
                message="Could not create manual chain test record; continuing with demo UI tracking.",
                metadata={"error": str(exc)},
            )
            return None

    def create_chain_phase(
        self,
        conn: Connection[Any],
        demo_run_id: int,
        chain_test_id: int | None,
        phase: dict[str, Any],
        resume_checkpoint_s3_uri: str | None,
    ) -> None:
        if not self.db.relation_exists("ml_ops", "manual_training_chain_phases"):
            return
        try:
            self.db.insert_dynamic(
                conn,
                "ml_ops",
                "manual_training_chain_phases",
                {
                    "demo_run_id": demo_run_id,
                    "linked_chain_test_id": chain_test_id,
                    "chain_test_id": chain_test_id,
                    "manual_training_chain_test_id": chain_test_id,
                    "test_id": chain_test_id,
                    "phase_no": phase["phase_no"],
                    "location_name": phase["location_name"],
                    "target_location_name": phase["location_name"],
                    "region_code": phase["region_code"],
                    "target_region_code": phase["region_code"],
                    "target_percent": phase["target_percent"],
                    "target_duration_seconds": phase["target_duration_seconds"],
                    "status": "PENDING",
                    "phase_status": "PENDING",
                    "model_id": self.settings.demo_model_id,
                    "model_version": self.settings.demo_model_version,
                    "resume_checkpoint_s3_uri": resume_checkpoint_s3_uri,
                    "input_checkpoint_s3_uri": resume_checkpoint_s3_uri,
                    "created_at": utc_now(),
                    "updated_at": utc_now(),
                },
                returning_candidates=["phase_id", "manual_training_chain_phase_id", "id"],
            )
        except Exception as exc:
            logger.warning("chain_phase_insert_failed", extra={"_phase_no": phase["phase_no"], "_error": str(exc)})
            self.create_event(
                conn,
                demo_run_id=demo_run_id,
                event_type="CHAIN_PHASE_COMPATIBILITY_WARNING",
                severity="WARN",
                message="Could not create compatible manual chain phase record.",
                phase_no=phase["phase_no"],
                metadata={"error": str(exc)},
            )

    def create_edge_command(
        self,
        conn: Connection[Any],
        demo_run_id: int,
        chain_test_id: int | None,
        phase: dict[str, Any],
        resume_checkpoint_s3_uri: str | None,
    ) -> int:
        if not self.db.relation_exists("ml_ops", "edge_training_commands"):
            raise RuntimeError("ml_ops.edge_training_commands does not exist.")

        columns = self.db.columns("ml_ops", "edge_training_commands")
        payload = {
            "demo_run_id": demo_run_id,
            "linked_chain_test_id": chain_test_id,
            "phase_no": phase["phase_no"],
            "target_percent": phase["target_percent"],
            "target_duration_seconds": phase["target_duration_seconds"],
            "target_location_name": phase["location_name"],
            "target_region_code": phase["region_code"],
            "model_id": self.settings.demo_model_id,
            "model_version": self.settings.demo_model_version,
            "resume_checkpoint_s3_uri": resume_checkpoint_s3_uri,
            "s3_bucket": self.settings.s3_bucket,
        }
        values: dict[str, Any] = {
            "command_type": self.settings.demo_edge_command_type,
            "type": self.settings.demo_edge_command_type,
            "command_status": "PENDING",
            "status": "PENDING",
            "demo_run_id": demo_run_id,
            "linked_demo_run_id": demo_run_id,
            "manual_demo_run_id": demo_run_id,
            "linked_chain_test_id": chain_test_id,
            "chain_test_id": chain_test_id,
            "manual_training_chain_test_id": chain_test_id,
            "phase_no": phase["phase_no"],
            "target_percent": phase["target_percent"],
            "target_duration_seconds": phase["target_duration_seconds"],
            "target_location_name": phase["location_name"],
            "location_name": phase["location_name"],
            "target_region_code": phase["region_code"],
            "region_code": phase["region_code"],
            "model_id": self.settings.demo_model_id,
            "model_version": self.settings.demo_model_version,
            "resume_checkpoint_s3_uri": resume_checkpoint_s3_uri,
            "input_checkpoint_s3_uri": resume_checkpoint_s3_uri,
            "parent_checkpoint_s3_uri": resume_checkpoint_s3_uri,
            "s3_bucket": self.settings.s3_bucket,
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }
        for column_name in ("command_payload", "payload", "metadata", "command_metadata"):
            if column_name in columns:
                values[column_name] = maybe_json_value(columns, column_name, payload)

        row = self.db.insert_dynamic(
            conn,
            "ml_ops",
            "edge_training_commands",
            values,
            returning_candidates=["command_id", "id"],
        )
        command_id = as_int(first_value(row, ["command_id", "id"]))
        if command_id is None:
            raise RuntimeError("Could not determine command_id after edge command insert.")

        self.create_event(
            conn,
            demo_run_id=demo_run_id,
            event_type="COMMAND_CREATED",
            message="Training command created for edge agent pickup.",
            location_name=phase["location_name"],
            region_code=phase["region_code"],
            phase_no=phase["phase_no"],
            command_id=command_id,
            metadata=payload,
        )
        return command_id

    def update_demo_run(self, conn: Connection[Any], demo_run_id: int, values: dict[str, Any]) -> None:
        values.setdefault("updated_at", utc_now())
        self.db.update_dynamic(conn, "ml_ops", "demo_ui_runs", values, "demo_run_id", demo_run_id)

    def create_event(
        self,
        conn: Connection[Any],
        *,
        demo_run_id: int,
        event_type: str,
        message: str,
        severity: str = "INFO",
        location_name: str | None = None,
        region_code: str | None = None,
        phase_no: int | None = None,
        command_id: int | None = None,
        training_run_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if not self.db.relation_exists("ml_ops", "demo_ui_events"):
            logger.info("demo_event", extra={"_event_type": event_type, "_message": message})
            return
        columns = self.db.columns("ml_ops", "demo_ui_events")
        self.db.insert_dynamic(
            conn,
            "ml_ops",
            "demo_ui_events",
            {
                "demo_run_id": demo_run_id,
                "event_type": event_type,
                "severity": severity,
                "message": message,
                "location_name": location_name,
                "region_code": region_code,
                "phase_no": phase_no,
                "command_id": command_id,
                "training_run_id": training_run_id,
                "metadata": maybe_json_value(columns, "metadata", metadata or {}) if metadata is not None else None,
                "created_at": utc_now(),
            },
            returning_candidates=["event_id", "id"],
        )

    def get_open_commands(self, conn: Connection[Any] | None = None) -> list[dict[str, Any]]:
        if not self.db.relation_exists("ml_ops", "edge_training_commands"):
            return []

        def query(connection: Connection[Any]) -> list[dict[str, Any]]:
            columns = self.db.columns("ml_ops", "edge_training_commands")
            status_column = "command_status" if "command_status" in columns else "status" if "status" in columns else None
            if not status_column:
                return []
            order_column = "updated_at" if "updated_at" in columns else "created_at" if "created_at" in columns else None
            order_sql = sql.SQL(" order by {} desc").format(sql.Identifier(order_column)) if order_column else sql.SQL("")
            query_sql = sql.SQL("select * from ml_ops.edge_training_commands where upper({}::text) = any(%s){} limit 20").format(
                sql.Identifier(status_column),
                order_sql,
            )
            rows = connection.execute(query_sql, (list(OPEN_COMMAND_STATUSES),)).fetchall()
            return [dict(row) for row in rows]

        if conn is not None:
            return query(conn)
        with self.db.connection() as new_conn:
            return query(new_conn)

    def get_command(self, command_id: int) -> dict[str, Any] | None:
        if not self.db.relation_exists("ml_ops", "edge_training_commands"):
            return None
        with self.db.connection() as conn:
            return self.get_command_with_conn(conn, command_id)

    def get_command_with_conn(self, conn: Connection[Any], command_id: int) -> dict[str, Any] | None:
        columns = self.db.columns("ml_ops", "edge_training_commands")
        id_column = "command_id" if "command_id" in columns else "id" if "id" in columns else None
        if not id_column:
            return None
        query_sql = sql.SQL("select * from ml_ops.edge_training_commands where {} = %s").format(sql.Identifier(id_column))
        row = conn.execute(query_sql, (command_id,)).fetchone()
        return dict(row) if row else None

    def command_status(self, command: dict[str, Any] | None) -> str | None:
        return normalize_status(first_value(command, ["command_status", "status", "current_status"]))

    def command_training_run_id(self, command: dict[str, Any] | None) -> int | None:
        return as_int(first_value(command, ["training_run_id", "output_training_run_id", "run_id"]))

    def command_checkpoint_uri(self, command: dict[str, Any] | None) -> str | None:
        if not command:
            return None
        value = first_value(
            command,
            [
                "output_checkpoint_s3_uri",
                "final_checkpoint_s3_uri",
                "checkpoint_s3_uri",
                "best_model_s3_uri",
                "output_artifact_s3_uri",
                "model_checkpoint_s3_uri",
            ],
        )
        if value:
            return str(value)
        for key in ("metadata", "payload", "command_payload", "result_payload"):
            payload = command.get(key)
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except ValueError:
                    payload = None
            if isinstance(payload, dict):
                value = first_value(
                    payload,
                    [
                        "output_checkpoint_s3_uri",
                        "final_checkpoint_s3_uri",
                        "checkpoint_s3_uri",
                        "best_model_s3_uri",
                    ],
                )
                if value:
                    return str(value)
        return None

    def latest_run_state(self, include_events: bool = True) -> DemoState:
        if not self.ui_tables_ready():
            return DemoState(
                setup_required=True,
                warning="Demo UI tables are missing. Run the SQL migrations before starting a demo.",
                phases=[DemoPhase(**phase) for phase in self.settings.phase_plan],
            )
        with self.db.connection() as conn:
            row = self._find_active_run(conn)
            if row is None:
                row = conn.execute(
                    "select * from ml_ops.demo_ui_runs order by created_at desc limit 1"
                ).fetchone()
                row = dict(row) if row else None
            if not row:
                return DemoState(phases=[DemoPhase(**phase) for phase in self.settings.phase_plan])
            return self.state_for_run_with_conn(conn, as_int(row["demo_run_id"]) or 0, include_events=include_events, run_row=row)

    def state_for_run(self, demo_run_id: int, include_events: bool = True) -> DemoState:
        if not self.ui_tables_ready():
            return DemoState(setup_required=True, warning="Demo UI tables are missing.")
        with self.db.connection() as conn:
            return self.state_for_run_with_conn(conn, demo_run_id, include_events=include_events)

    def state_for_run_with_conn(
        self,
        conn: Connection[Any],
        demo_run_id: int,
        *,
        include_events: bool = True,
        run_row: dict[str, Any] | None = None,
    ) -> DemoState:
        if run_row is None:
            row = conn.execute("select * from ml_ops.demo_ui_runs where demo_run_id = %s", (demo_run_id,)).fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demo run not found")
            run_row = dict(row)
        events = self.events_for_run_with_conn(conn, demo_run_id, limit=200 if include_events else 20)
        phases = self._build_phases(conn, events)
        current_command_id = as_int(first_value(run_row, ["current_command_id"]))
        latest_metrics = self.latest_metrics_with_conn(conn, current_command_id, run_row)
        status_value = normalize_status(run_row.get("status")) or "UNKNOWN"
        progress = self._overall_progress(status_value, phases, latest_metrics)
        current_phase = self._current_phase(run_row, phases)
        latest_checkpoint = next(
            (phase.output_checkpoint_s3_uri for phase in reversed(phases) if phase.output_checkpoint_s3_uri),
            None,
        )
        final_checkpoint = first_value(run_row, ["final_checkpoint_s3_uri"]) or latest_checkpoint
        final_training_run_id = as_int(first_value(run_row, ["final_training_run_id"])) or (
            phases[-1].training_run_id if phases else None
        )

        return DemoState(
            demo_run_id=as_int(run_row.get("demo_run_id")),
            demo_name=run_row.get("demo_name"),
            status=status_value,
            overall_progress_percent=round(progress, 2),
            current_phase=current_phase,
            phases=phases,
            latest_metrics=latest_metrics,
            latest_checkpoint_s3_uri=latest_checkpoint,
            final_result=FinalResult(
                final_training_run_id=final_training_run_id,
                final_checkpoint_s3_uri=str(final_checkpoint) if final_checkpoint else None,
                best_model_s3_uri=self._best_model_uri(conn, current_command_id),
            ),
            events=events if include_events else [],
            created_at=run_row.get("created_at"),
            started_at=run_row.get("started_at"),
            finished_at=run_row.get("finished_at"),
            updated_at=run_row.get("updated_at"),
        )

    def events_for_run(self, demo_run_id: int, limit: int = 200) -> list[DemoEvent]:
        if not self.ui_tables_ready():
            return []
        with self.db.connection() as conn:
            return self.events_for_run_with_conn(conn, demo_run_id, limit=limit)

    def events_for_run_with_conn(self, conn: Connection[Any], demo_run_id: int, limit: int = 200) -> list[DemoEvent]:
        rows = conn.execute(
            """
            select *
            from ml_ops.demo_ui_events
            where demo_run_id = %s
            order by created_at asc, event_id asc
            limit %s
            """,
            (demo_run_id, limit),
        ).fetchall()
        return [
            DemoEvent(
                event_id=as_int(row.get("event_id")),
                demo_run_id=as_int(row.get("demo_run_id")) or demo_run_id,
                event_type=str(row.get("event_type")),
                severity=str(row.get("severity") or "INFO"),
                message=str(row.get("message") or ""),
                location_name=row.get("location_name"),
                region_code=row.get("region_code"),
                phase_no=as_int(row.get("phase_no")),
                command_id=as_int(row.get("command_id")),
                training_run_id=as_int(row.get("training_run_id")),
                metadata=row.get("metadata") if isinstance(row.get("metadata"), dict) else None,
                created_at=row.get("created_at") or utc_now(),
            )
            for row in rows
        ]

    def _build_phases(self, conn: Connection[Any], events: list[DemoEvent]) -> list[DemoPhase]:
        phases = {phase["phase_no"]: DemoPhase(**phase) for phase in self.settings.phase_plan}
        for event in events:
            if not event.phase_no or event.phase_no not in phases:
                continue
            phase = phases[event.phase_no]
            if event.event_type == "PHASE_STARTED":
                phase.status = "RUNNING"
                phase.started_at = event.created_at
            elif event.event_type == "COMMAND_CREATED":
                phase.command_id = event.command_id
                phase.command_status = "PENDING"
            elif event.event_type in {"COMMAND_PICKED_UP", "TRAINING_STARTED"}:
                phase.status = "RUNNING"
                phase.command_status = "RUNNING"
            elif event.event_type == "PHASE_COMPLETED":
                phase.status = "COMPLETED"
                phase.command_status = "COMPLETED"
                phase.completed_at = event.created_at
                phase.training_run_id = event.training_run_id
                if event.metadata:
                    checkpoint = first_value(event.metadata, ["output_checkpoint_s3_uri", "final_checkpoint_s3_uri"])
                    phase.output_checkpoint_s3_uri = str(checkpoint) if checkpoint else phase.output_checkpoint_s3_uri
            elif event.event_type in {"PHASE_FAILED", "DEMO_FAILED"}:
                phase.status = "FAILED"
                phase.command_status = "FAILED"

        for phase in phases.values():
            if not phase.command_id:
                continue
            command = self.get_command_with_conn(conn, phase.command_id)
            command_status = self.command_status(command)
            if command_status:
                phase.command_status = command_status
                if command_status in COMPLETED_COMMAND_STATUSES:
                    phase.status = "COMPLETED"
                elif command_status in FAILED_COMMAND_STATUSES:
                    phase.status = "FAILED"
                elif command_status in OPEN_COMMAND_STATUSES:
                    phase.status = "RUNNING"
            phase.training_run_id = self.command_training_run_id(command) or phase.training_run_id
            phase.output_checkpoint_s3_uri = self.command_checkpoint_uri(command) or phase.output_checkpoint_s3_uri
        return [phases[number] for number in sorted(phases)]

    def latest_metrics_with_conn(
        self,
        conn: Connection[Any],
        current_command_id: int | None,
        run_row: dict[str, Any],
    ) -> LiveMetrics | None:
        relation = None
        if self.db.relation_exists("ml_ops", "vw_training_live_latest_metrics"):
            relation = "vw_training_live_latest_metrics"
        elif self.db.relation_exists("ml_ops", "training_live_metrics"):
            relation = "training_live_metrics"
        if relation is None:
            return None

        columns = self.db.columns("ml_ops", relation)
        where_sql = sql.SQL("")
        params: tuple[Any, ...] = ()
        if current_command_id and "command_id" in columns:
            where_sql = sql.SQL(" where command_id = %s")
            params = (current_command_id,)
        elif run_row.get("final_training_run_id") and "training_run_id" in columns:
            where_sql = sql.SQL(" where training_run_id = %s")
            params = (run_row["final_training_run_id"],)

        order_column = "updated_at" if "updated_at" in columns else "created_at" if "created_at" in columns else None
        order_sql = sql.SQL(" order by {} desc").format(sql.Identifier(order_column)) if order_column else sql.SQL("")
        query_sql = sql.SQL("select * from ml_ops.{}{}{} limit 1").format(
            sql.Identifier(relation),
            where_sql,
            order_sql,
        )
        row = conn.execute(query_sql, params).fetchone()
        if not row:
            return None
        data = dict(row)
        return LiveMetrics(
            command_id=as_int(first_value(data, ["command_id"])),
            training_run_id=as_int(first_value(data, ["training_run_id", "run_id"])),
            current_status=normalize_status(first_value(data, ["current_status", "status", "training_status"])),
            progress_percent=as_float(first_value(data, ["progress_percent", "progress", "training_progress_percent"])),
            epoch=as_int(first_value(data, ["epoch", "current_epoch"])),
            total_epochs=as_int(first_value(data, ["total_epochs", "epochs"])),
            map50=as_float(first_value(data, ["map50", "mAP50", "map_50", "metrics_map50"])),
            precision=as_float(first_value(data, ["precision", "metrics_precision"])),
            recall=as_float(first_value(data, ["recall", "metrics_recall"])),
            message=first_value(data, ["message", "status_message"]),
            updated_at=first_value(data, ["updated_at", "created_at"]),
        )

    def _best_model_uri(self, conn: Connection[Any], current_command_id: int | None) -> str | None:
        if not current_command_id:
            return None
        command = self.get_command_with_conn(conn, current_command_id)
        value = first_value(command, ["best_model_s3_uri", "best_model_uri"])
        return str(value) if value else None

    def _current_phase(self, run_row: dict[str, Any], phases: list[DemoPhase]) -> CurrentPhase | None:
        current_phase_no = as_int(run_row.get("current_phase_no"))
        phase = next((item for item in phases if item.phase_no == current_phase_no), None)
        if phase is None:
            phase = next((item for item in phases if item.status == "RUNNING"), None)
        if phase is None:
            phase = next((item for item in phases if item.status == "PENDING"), None)
        if phase is None and phases:
            phase = phases[-1]
        if phase is None:
            return None
        return CurrentPhase(
            phase_no=phase.phase_no,
            location_name=phase.location_name,
            region_code=phase.region_code,
            target_percent=phase.target_percent,
            status=phase.status,
            command_id=phase.command_id,
            training_run_id=phase.training_run_id,
        )

    def _overall_progress(self, status_value: str, phases: list[DemoPhase], latest_metrics: LiveMetrics | None) -> float:
        if status_value == "COMPLETED":
            return 100.0
        if status_value in {"FAILED", "CANCELLED"}:
            completed = sum(phase.target_percent for phase in phases if phase.status == "COMPLETED")
            return min(100.0, float(completed))
        completed = sum(phase.target_percent for phase in phases if phase.status == "COMPLETED")
        running = next((phase for phase in phases if phase.status == "RUNNING"), None)
        if running and latest_metrics and latest_metrics.progress_percent is not None:
            completed += running.target_percent * max(0.0, min(100.0, latest_metrics.progress_percent)) / 100.0
        return min(100.0, float(completed))

    def reset_stale(self, user: SessionUser, mark_open_commands_failed: bool, reason: str | None) -> tuple[int, int]:
        self.require_ui_tables()
        with self.db.connection() as conn:
            with conn.transaction():
                active_rows = conn.execute(
                    "select demo_run_id from ml_ops.demo_ui_runs where status = any(%s)",
                    (list(ACTIVE_RUN_STATUSES),),
                ).fetchall()
                reset_runs = conn.execute(
                    """
                    update ml_ops.demo_ui_runs
                    set status = 'FAILED',
                        error_message = %s,
                        finished_at = coalesce(finished_at, now()),
                        updated_at = now()
                    where status = any(%s)
                    """,
                    (reason or f"Reset by {user.subject}", list(ACTIVE_RUN_STATUSES)),
                ).rowcount or 0

                reset_commands = 0
                if mark_open_commands_failed and self.db.relation_exists("ml_ops", "edge_training_commands"):
                    columns = self.db.columns("ml_ops", "edge_training_commands")
                    status_column = "command_status" if "command_status" in columns else "status" if "status" in columns else None
                    if status_column:
                        update_sql = sql.SQL(
                            "update ml_ops.edge_training_commands set {} = 'FAILED'{} where upper({}::text) = any(%s)"
                        ).format(
                            sql.Identifier(status_column),
                            sql.SQL(", updated_at = now()") if "updated_at" in columns else sql.SQL(""),
                            sql.Identifier(status_column),
                        )
                        reset_commands = conn.execute(update_sql, (list(OPEN_COMMAND_STATUSES),)).rowcount or 0

                for row in active_rows:
                    demo_run_id = as_int(row.get("demo_run_id"))
                    if demo_run_id:
                        self.create_event(
                            conn,
                            demo_run_id=demo_run_id,
                            event_type="STALE_STATE_RESET",
                            severity="WARN",
                            message="Stale demo state was marked failed by an administrator.",
                            metadata={
                                "reset_by": user.subject,
                                "reason": reason,
                                "mark_open_commands_failed": mark_open_commands_failed,
                                "reset_commands": reset_commands,
                            },
                        )
                return reset_runs, reset_commands

