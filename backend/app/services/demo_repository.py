import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from psycopg import Connection, sql
from psycopg.types.json import Jsonb

from app.config import Settings
from app.db.introspection import first_existing, get_columns, table_exists
from app.schemas.demo import DemoEvent, DemoPhase, DemoRunState, FinalResult, LiveMetrics, SiteInfo


OPEN_COMMAND_STATUSES = ("PENDING", "PICKED_UP", "RUNNING")
ACTIVE_RUN_STATUSES = ("STARTING", "RUNNING", "TRANSITION")


@dataclass(frozen=True)
class PhasePlan:
    phase_no: int
    location_name: str
    region_code: str
    target_percent: int
    target_duration_seconds: int


def phase_plan(settings: Settings) -> list[PhasePlan]:
    return [
        PhasePlan(1, settings.site_wiener_neustadt_location_name, settings.site_wiener_neustadt_region_code, 20, 60),
        PhasePlan(2, settings.site_wien_location_name, settings.site_wien_region_code, 30, 90),
        PhasePlan(3, settings.site_eisenstadt_location_name, settings.site_eisenstadt_region_code, 30, 90),
        PhasePlan(4, settings.site_wiener_neustadt_location_name, settings.site_wiener_neustadt_region_code, 20, 60),
    ]


def configured_sites(settings: Settings) -> list[SiteInfo]:
    return [
        SiteInfo(
            location_name=settings.site_wiener_neustadt_location_name,
            region_code=settings.site_wiener_neustadt_region_code,
            host_label="ec2-wiener-neustadt",
            role="existing central/cloud training site",
        ),
        SiteInfo(
            location_name=settings.site_wien_location_name,
            region_code=settings.site_wien_region_code,
            host_label="cloud-pi-wien",
            role="temporary cloud replacement for Raspberry Pi Wien",
        ),
        SiteInfo(
            location_name=settings.site_eisenstadt_location_name,
            region_code=settings.site_eisenstadt_region_code,
            host_label="cloud-pi-eisenstadt",
            role="temporary cloud replacement for Raspberry Pi Eisenstadt",
        ),
    ]


class MigrationRequiredError(RuntimeError):
    pass


class DemoRepository:
    def __init__(self, conn: Connection, settings: Settings):
        self.conn = conn
        self.settings = settings

    def ui_tables_available(self) -> bool:
        return table_exists(self.conn, "ml_ops", "demo_ui_runs") and table_exists(self.conn, "ml_ops", "demo_ui_events")

    def ensure_ui_tables(self) -> None:
        if not self.ui_tables_available():
            raise MigrationRequiredError("Demo UI tables are missing. Run backend/sql migrations first.")

    def active_demo_run(self) -> dict[str, Any] | None:
        self.ensure_ui_tables()
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT *
                FROM ml_ops.demo_ui_runs
                WHERE status = ANY(%s)
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (list(ACTIVE_RUN_STATUSES),),
            )
            return cur.fetchone()

    def latest_demo_run(self) -> dict[str, Any] | None:
        self.ensure_ui_tables()
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT *
                FROM ml_ops.demo_ui_runs
                ORDER BY created_at DESC
                LIMIT 1
                """
            )
            return cur.fetchone()

    def create_demo_run(self, started_by: str, auth_subject: str) -> int:
        self.ensure_ui_tables()
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ml_ops.demo_ui_runs (
                    demo_name,
                    status,
                    requested_duration_seconds,
                    started_by,
                    auth_subject,
                    started_at
                )
                VALUES (%s, 'STARTING', %s, %s, %s, now())
                RETURNING demo_run_id
                """,
                (
                    "Sustainable AI 5-minute multi-site demo",
                    self.settings.demo_total_duration_seconds,
                    started_by,
                    auth_subject,
                ),
            )
            demo_run_id = int(cur.fetchone()["demo_run_id"])
        self.add_event(demo_run_id, "DEMO_STARTED", "Demo started from web interface", severity="INFO")
        return demo_run_id

    def update_demo_run(self, demo_run_id: int, **fields: Any) -> None:
        self.ensure_ui_tables()
        if not fields:
            return
        fields["updated_at"] = datetime.now(timezone.utc)
        assignments = [sql.SQL("{} = {}").format(sql.Identifier(key), sql.Placeholder(key)) for key in fields]
        query = sql.SQL("UPDATE ml_ops.demo_ui_runs SET {} WHERE demo_run_id = {}").format(
            sql.SQL(", ").join(assignments),
            sql.Placeholder("demo_run_id"),
        )
        params = fields | {"demo_run_id": demo_run_id}
        with self.conn.cursor() as cur:
            cur.execute(query, params)

    def add_event(
        self,
        demo_run_id: int,
        event_type: str,
        message: str,
        *,
        severity: str = "INFO",
        location_name: str | None = None,
        region_code: str | None = None,
        phase_no: int | None = None,
        command_id: int | None = None,
        training_run_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.ensure_ui_tables()
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ml_ops.demo_ui_events (
                    demo_run_id,
                    event_type,
                    severity,
                    message,
                    location_name,
                    region_code,
                    phase_no,
                    command_id,
                    training_run_id,
                    metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    demo_run_id,
                    event_type,
                    severity,
                    message,
                    location_name,
                    region_code,
                    phase_no,
                    command_id,
                    training_run_id,
                    Jsonb(metadata) if metadata is not None else None,
                ),
            )

    def list_events(self, demo_run_id: int, limit: int = 200) -> list[dict[str, Any]]:
        self.ensure_ui_tables()
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT *
                FROM ml_ops.demo_ui_events
                WHERE demo_run_id = %s
                ORDER BY created_at ASC
                LIMIT %s
                """,
                (demo_run_id, limit),
            )
            return cur.fetchall()

    def open_edge_commands(self, limit: int = 20) -> list[dict[str, Any]]:
        if not table_exists(self.conn, "ml_ops", "edge_training_commands"):
            return []
        columns = get_columns(self.conn, "ml_ops", "edge_training_commands")
        status_col = first_existing(columns, ["command_status", "status"])
        id_col = first_existing(columns, ["command_id", "id"])
        if not status_col:
            return []
        select_cols = [
            col
            for col in [id_col, status_col, "target_location_name", "location_name", "target_region_code", "region_code", "created_at", "updated_at"]
            if col and col in columns
        ]
        order_col = first_existing(columns, ["updated_at", "created_at"])
        order_sql = sql.SQL(" ORDER BY {} DESC NULLS LAST").format(sql.Identifier(order_col)) if order_col else sql.SQL("")
        query = sql.SQL("SELECT {} FROM ml_ops.edge_training_commands WHERE {} = ANY(%s){} LIMIT %s").format(
            sql.SQL(", ").join(sql.Identifier(col) for col in dict.fromkeys(select_cols)),
            sql.Identifier(status_col),
            order_sql,
        )
        with self.conn.cursor() as cur:
            cur.execute(query, (list(OPEN_COMMAND_STATUSES), limit))
            return cur.fetchall()

    def create_chain_test_if_possible(self, demo_run_id: int) -> int | None:
        if not table_exists(self.conn, "ml_ops", "manual_training_chain_tests"):
            return None
        columns = get_columns(self.conn, "ml_ops", "manual_training_chain_tests")
        id_col = first_existing(columns, ["chain_test_id", "manual_training_chain_test_id", "test_id", "id"])
        values: dict[str, Any] = {
            "demo_name": "Sustainable AI Demo Interface run",
            "test_name": "Sustainable AI Demo Interface run",
            "status": "RUNNING",
            "total_duration_seconds": self.settings.demo_total_duration_seconds,
            "requested_duration_seconds": self.settings.demo_total_duration_seconds,
            "model_id": self.settings.demo_model_id,
            "model_version": self.settings.demo_model_version,
            "demo_run_id": demo_run_id,
            "created_at": datetime.now(timezone.utc),
            "started_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        insert_values = {key: value for key, value in values.items() if key in columns}
        if not insert_values or not id_col:
            return None
        query = sql.SQL("INSERT INTO ml_ops.manual_training_chain_tests ({}) VALUES ({}) RETURNING {}").format(
            sql.SQL(", ").join(sql.Identifier(k) for k in insert_values),
            sql.SQL(", ").join(sql.Placeholder(k) for k in insert_values),
            sql.Identifier(id_col),
        )
        with self.conn.cursor() as cur:
            cur.execute(query, insert_values)
            return int(cur.fetchone()[id_col])

    def upsert_chain_phase_if_possible(
        self,
        linked_chain_test_id: int | None,
        plan: PhasePlan,
        *,
        status: str,
        command_id: int | None = None,
        training_run_id: int | None = None,
        resume_checkpoint_s3_uri: str | None = None,
        output_checkpoint_s3_uri: str | None = None,
    ) -> None:
        if linked_chain_test_id is None or not table_exists(self.conn, "ml_ops", "manual_training_chain_phases"):
            return
        columns = get_columns(self.conn, "ml_ops", "manual_training_chain_phases")
        values: dict[str, Any] = {
            "chain_test_id": linked_chain_test_id,
            "manual_training_chain_test_id": linked_chain_test_id,
            "phase_no": plan.phase_no,
            "location_name": plan.location_name,
            "target_location_name": plan.location_name,
            "region_code": plan.region_code,
            "target_region_code": plan.region_code,
            "target_percent": plan.target_percent,
            "target_minutes": plan.target_duration_seconds / 60.0,
            "target_duration_seconds": plan.target_duration_seconds,
            "status": status,
            "command_status": status,
            "command_id": command_id,
            "training_run_id": training_run_id,
            "resume_checkpoint_s3_uri": resume_checkpoint_s3_uri,
            "output_checkpoint_s3_uri": output_checkpoint_s3_uri,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        insert_values = {key: value for key, value in values.items() if key in columns and value is not None}
        if not insert_values:
            return
        chain_col = first_existing(columns, ["chain_test_id", "manual_training_chain_test_id"])
        if chain_col and "phase_no" in columns:
            update_values = {
                key: value
                for key, value in insert_values.items()
                if key not in {chain_col, "chain_test_id", "manual_training_chain_test_id", "phase_no", "created_at"}
            }
            if update_values:
                update_query = sql.SQL("UPDATE ml_ops.manual_training_chain_phases SET {} WHERE {} = {} AND phase_no = {}").format(
                    sql.SQL(", ").join(
                        sql.SQL("{} = {}").format(sql.Identifier(key), sql.Placeholder(key)) for key in update_values
                    ),
                    sql.Identifier(chain_col),
                    sql.Placeholder("chain_where"),
                    sql.Placeholder("phase_where"),
                )
                with self.conn.cursor() as cur:
                    cur.execute(update_query, update_values | {"chain_where": linked_chain_test_id, "phase_where": plan.phase_no})
                    if cur.rowcount > 0:
                        return
        query = sql.SQL("INSERT INTO ml_ops.manual_training_chain_phases ({}) VALUES ({})").format(
            sql.SQL(", ").join(sql.Identifier(k) for k in insert_values),
            sql.SQL(", ").join(sql.Placeholder(k) for k in insert_values),
        )
        with self.conn.cursor() as cur:
            cur.execute(query, insert_values)

    def update_chain_test_if_possible(
        self,
        linked_chain_test_id: int | None,
        *,
        status: str,
        final_training_run_id: int | None = None,
        final_checkpoint_s3_uri: str | None = None,
        error_message: str | None = None,
    ) -> None:
        if linked_chain_test_id is None or not table_exists(self.conn, "ml_ops", "manual_training_chain_tests"):
            return
        columns = get_columns(self.conn, "ml_ops", "manual_training_chain_tests")
        id_col = first_existing(columns, ["chain_test_id", "manual_training_chain_test_id", "test_id", "id"])
        if not id_col:
            return
        values: dict[str, Any] = {
            "status": status,
            "final_training_run_id": final_training_run_id,
            "training_run_id": final_training_run_id,
            "final_checkpoint_s3_uri": final_checkpoint_s3_uri,
            "output_checkpoint_s3_uri": final_checkpoint_s3_uri,
            "error_message": error_message,
            "finished_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        update_values = {key: value for key, value in values.items() if key in columns and value is not None}
        if not update_values:
            return
        query = sql.SQL("UPDATE ml_ops.manual_training_chain_tests SET {} WHERE {} = {}").format(
            sql.SQL(", ").join(sql.SQL("{} = {}").format(sql.Identifier(k), sql.Placeholder(k)) for k in update_values),
            sql.Identifier(id_col),
            sql.Placeholder("id_value"),
        )
        with self.conn.cursor() as cur:
            cur.execute(query, update_values | {"id_value": linked_chain_test_id})

    def insert_edge_command(self, demo_run_id: int, plan: PhasePlan, resume_checkpoint_s3_uri: str | None) -> int:
        if not table_exists(self.conn, "ml_ops", "edge_training_commands"):
            raise RuntimeError("ml_ops.edge_training_commands does not exist.")
        columns = get_columns(self.conn, "ml_ops", "edge_training_commands")
        id_col = first_existing(columns, ["command_id", "id"])
        if not id_col:
            raise RuntimeError("Could not find command id column in ml_ops.edge_training_commands.")

        payload = {
            "source": "sustainable-ai-demo-interface",
            "demo_run_id": demo_run_id,
            "phase_no": plan.phase_no,
            "target_percent": plan.target_percent,
            "target_minutes": plan.target_duration_seconds / 60.0,
            "target_duration_seconds": plan.target_duration_seconds,
            "target_location_name": plan.location_name,
            "target_region_code": plan.region_code,
            "model_id": self.settings.demo_model_id,
            "model_version": self.settings.demo_model_version,
            "resume_checkpoint_s3_uri": resume_checkpoint_s3_uri,
            "s3_bucket": self.settings.s3_bucket,
        }
        values: dict[str, Any] = {
            "command_type": "START_TRAINING",
            "command_name": f"demo-phase-{plan.phase_no}",
            "command_status": "PENDING",
            "status": "PENDING",
            "target_location_name": plan.location_name,
            "location_name": plan.location_name,
            "target_region_code": plan.region_code,
            "region_code": plan.region_code,
            "model_id": self.settings.demo_model_id,
            "model_version": self.settings.demo_model_version,
            "phase_no": plan.phase_no,
            "target_percent": plan.target_percent,
            "target_minutes": plan.target_duration_seconds / 60.0,
            "target_duration_seconds": plan.target_duration_seconds,
            "resume_checkpoint_s3_uri": resume_checkpoint_s3_uri,
            "requested_by": "sustainable-ai-demo-interface",
            "source": "sustainable-ai-demo-interface",
            "command_payload": Jsonb(payload),
            "payload": Jsonb(payload),
            "parameters": Jsonb(payload),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        insert_values = {key: value for key, value in values.items() if key in columns}
        query = sql.SQL("INSERT INTO ml_ops.edge_training_commands ({}) VALUES ({}) RETURNING {}").format(
            sql.SQL(", ").join(sql.Identifier(k) for k in insert_values),
            sql.SQL(", ").join(sql.Placeholder(k) for k in insert_values),
            sql.Identifier(id_col),
        )
        with self.conn.cursor() as cur:
            cur.execute(query, insert_values)
            return int(cur.fetchone()[id_col])

    def get_command(self, command_id: int) -> dict[str, Any] | None:
        if not table_exists(self.conn, "ml_ops", "edge_training_commands"):
            return None
        columns = get_columns(self.conn, "ml_ops", "edge_training_commands")
        id_col = first_existing(columns, ["command_id", "id"])
        if not id_col:
            return None
        with self.conn.cursor() as cur:
            cur.execute(
                sql.SQL("SELECT * FROM ml_ops.edge_training_commands WHERE {} = %s").format(sql.Identifier(id_col)),
                (command_id,),
            )
            return cur.fetchone()

    def command_status(self, command: dict[str, Any] | None) -> str:
        if not command:
            return "UNKNOWN"
        return str(command.get("command_status") or command.get("status") or "UNKNOWN").upper()

    def latest_metrics(self, command_id: int | None, training_run_id: int | None) -> dict[str, Any] | None:
        source_table = None
        if table_exists(self.conn, "ml_ops", "vw_training_live_latest_metrics"):
            source_table = "vw_training_live_latest_metrics"
        elif table_exists(self.conn, "ml_ops", "training_live_metrics"):
            source_table = "training_live_metrics"
        if source_table is None:
            return None
        columns = get_columns(self.conn, "ml_ops", source_table)
        filters = []
        params: list[Any] = []
        if command_id is not None and "command_id" in columns:
            filters.append(sql.SQL("command_id = %s"))
            params.append(command_id)
        if training_run_id is not None and "training_run_id" in columns:
            filters.append(sql.SQL("training_run_id = %s"))
            params.append(training_run_id)
        where = sql.SQL("WHERE {}").format(sql.SQL(" OR ").join(filters)) if filters else sql.SQL("")
        updated_col = first_existing(columns, ["updated_at", "created_at", "event_time", "timestamp"])
        order = sql.SQL("ORDER BY {} DESC NULLS LAST").format(sql.Identifier(updated_col)) if updated_col else sql.SQL("")
        query = sql.SQL("SELECT * FROM ml_ops.{} {} {} LIMIT 1").format(sql.Identifier(source_table), where, order)
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchone()

    def build_state(self, run_row: dict[str, Any], include_events: bool = True) -> DemoRunState:
        events = self.list_events(int(run_row["demo_run_id"])) if include_events else []
        phases = self._build_phases(run_row, events)
        current_phase = next((phase for phase in phases if phase.phase_no == run_row.get("current_phase_no")), None)
        latest_metrics_row = self.latest_metrics(run_row.get("current_command_id"), current_phase.training_run_id if current_phase else None)
        latest_metrics = self._map_metrics(latest_metrics_row)
        overall = self._overall_progress(run_row, phases, current_phase, latest_metrics)
        final_uri = run_row.get("final_checkpoint_s3_uri")
        final = FinalResult(
            final_training_run_id=run_row.get("final_training_run_id"),
            final_checkpoint_s3_uri=final_uri,
            s3_best_model_uri=final_uri,
        )
        return DemoRunState(
            demo_run_id=int(run_row["demo_run_id"]),
            demo_name=run_row["demo_name"],
            status=run_row["status"],
            overall_progress_percent=overall,
            requested_duration_seconds=int(run_row["requested_duration_seconds"]),
            started_by=run_row.get("started_by"),
            auth_subject=run_row.get("auth_subject"),
            current_phase=current_phase,
            phases=phases,
            latest_metrics=latest_metrics,
            final_result=final,
            events=[DemoEvent(**event) for event in events],
            error_message=run_row.get("error_message"),
            created_at=run_row["created_at"],
            started_at=run_row.get("started_at"),
            finished_at=run_row.get("finished_at"),
            updated_at=run_row["updated_at"],
        )

    def _build_phases(self, run_row: dict[str, Any], events: list[dict[str, Any]]) -> list[DemoPhase]:
        result = []
        current_phase_no = run_row.get("current_phase_no")
        run_status = str(run_row.get("status"))
        for plan in phase_plan(self.settings):
            phase_events = [event for event in events if event.get("phase_no") == plan.phase_no]
            command_id = next((event.get("command_id") for event in reversed(phase_events) if event.get("command_id")), None)
            training_run_id = next((event.get("training_run_id") for event in reversed(phase_events) if event.get("training_run_id")), None)
            metadata = {}
            for event in phase_events:
                if isinstance(event.get("metadata"), dict):
                    metadata.update(event["metadata"])
            command = self.get_command(command_id) if command_id else None
            command_status = self.command_status(command)
            if any(event["event_type"] == "PHASE_COMPLETED" for event in phase_events):
                status = "COMPLETED"
            elif any(event["event_type"] == "PHASE_FAILED" for event in phase_events):
                status = "FAILED"
            elif current_phase_no == plan.phase_no and run_status in ACTIVE_RUN_STATUSES:
                status = "RUNNING" if command_status in {"PICKED_UP", "RUNNING"} else "PENDING"
            elif current_phase_no and plan.phase_no < int(current_phase_no):
                status = "COMPLETED"
            else:
                status = "PENDING"
            result.append(
                DemoPhase(
                    phase_no=plan.phase_no,
                    location_name=plan.location_name,
                    region_code=plan.region_code,
                    target_percent=plan.target_percent,
                    target_duration_seconds=plan.target_duration_seconds,
                    status=status,
                    command_id=command_id,
                    command_status=command_status if command_id else None,
                    training_run_id=training_run_id or (command or {}).get("training_run_id"),
                    resume_checkpoint_s3_uri=metadata.get("resume_checkpoint_s3_uri"),
                    output_checkpoint_s3_uri=metadata.get("output_checkpoint_s3_uri")
                    or (command or {}).get("output_checkpoint_s3_uri")
                    or (command or {}).get("checkpoint_s3_uri"),
                )
            )
        return result

    def _map_metrics(self, row: dict[str, Any] | None) -> LiveMetrics | None:
        if not row:
            return None
        def pick(*names: str) -> Any:
            for name in names:
                if name in row and row[name] is not None:
                    return row[name]
            return None

        return LiveMetrics(
            command_id=pick("command_id"),
            training_run_id=pick("training_run_id", "run_id"),
            current_status=pick("current_status", "status", "training_status"),
            progress_percent=pick("progress_percent", "progress"),
            epoch=pick("epoch", "current_epoch"),
            total_epochs=pick("total_epochs", "epochs"),
            map50=pick("map50", "mAP50", "map_50"),
            precision=pick("precision"),
            recall=pick("recall"),
            message=pick("message", "status_message"),
            updated_at=pick("updated_at", "created_at", "timestamp", "event_time"),
        )

    def _overall_progress(
        self,
        run_row: dict[str, Any],
        phases: list[DemoPhase],
        current_phase: DemoPhase | None,
        latest_metrics: LiveMetrics | None,
    ) -> float:
        if run_row["status"] == "COMPLETED":
            return 100.0
        completed = sum(phase.target_percent for phase in phases if phase.status == "COMPLETED")
        if current_phase and latest_metrics and latest_metrics.progress_percent is not None:
            completed += current_phase.target_percent * min(max(latest_metrics.progress_percent, 0.0), 100.0) / 100.0
        return round(min(completed, 100.0), 2)

    def reset_stale(self, fail_open_commands: bool) -> tuple[int, int]:
        self.ensure_ui_tables()
        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE ml_ops.demo_ui_runs
                SET status = 'FAILED',
                    error_message = COALESCE(error_message, 'Reset stale demo state from UI'),
                    finished_at = COALESCE(finished_at, now()),
                    updated_at = now()
                WHERE status = ANY(%s)
                """,
                (list(ACTIVE_RUN_STATUSES),),
            )
            reset_runs = cur.rowcount
        reset_commands = 0
        if fail_open_commands and table_exists(self.conn, "ml_ops", "edge_training_commands"):
            columns = get_columns(self.conn, "ml_ops", "edge_training_commands")
            status_col = first_existing(columns, ["command_status", "status"])
            if status_col:
                with self.conn.cursor() as cur:
                    cur.execute(
                        sql.SQL("UPDATE ml_ops.edge_training_commands SET {} = 'FAILED' WHERE {} = ANY(%s)").format(
                            sql.Identifier(status_col),
                            sql.Identifier(status_col),
                        ),
                        (list(OPEN_COMMAND_STATUSES),),
                    )
                    reset_commands = cur.rowcount
        return reset_runs, reset_commands
