import hashlib
import hmac
import json
import re
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from psycopg import Connection, sql

from app.config import Settings
from app.db.introspection import first_existing, get_columns, table_exists
from app.schemas.demo import DemoPhase, DemoRunState
from app.services.demo_repository import DemoRepository


class CertificateError(RuntimeError):
    status_code = 400


class CertificateNotFoundError(CertificateError):
    status_code = 404


class CertificateNotReadyError(CertificateError):
    status_code = 409


class CertificateConfigurationError(CertificateError):
    status_code = 503


class CertificateService:
    def __init__(self, conn: Connection, settings: Settings):
        self.conn = conn
        self.settings = settings
        self.repo = DemoRepository(conn, settings)

    def generate_certificate(self, demo_run_id: int) -> dict[str, Any]:
        if not self.settings.certificate_signing_secret:
            raise CertificateConfigurationError("CERTIFICATE_SIGNING_SECRET is not configured.")

        run_row = self._get_run(demo_run_id)
        if str(run_row.get("status")).upper() != "COMPLETED":
            raise CertificateNotReadyError("Digital certificate can only be exported for a completed demo run.")

        state = self.repo.build_state(run_row)
        phases = self._build_certificate_phases(run_row, state)
        final_checkpoint = state.final_result.final_checkpoint_s3_uri or self._last_checkpoint(phases)

        if not final_checkpoint and phases:
            final_checkpoint = phases[-1].get("output_checkpoint_s3_uri")

        payload = {
            "certificate_type": "SUSTAINABLE_AI_TRAINING_CERTIFICATE",
            "certificate_version": "1.0",
            "certificate_id": f"sai-cert-{demo_run_id}-{uuid4()}",
            "issued_at": datetime.now(timezone.utc).isoformat(),
            "issuer": self.settings.certificate_issuer,
            "demo_run_id": state.demo_run_id,
            "demo_name": state.demo_name,
            "status": state.status,
            "started_at": self._json_value(state.started_at),
            "finished_at": self._json_value(state.finished_at),
            "final_training_run_id": state.final_result.final_training_run_id,
            "final_checkpoint_s3_uri": final_checkpoint,
            "model_id": self.settings.demo_model_id,
            "model_version": self.settings.demo_model_version,
            "training_type": "YOLO object detection",
            "use_case": "Industrial safety equipment detection",
            "phases": phases,
        }

        payload_sha256 = hashlib.sha256(self._canonical_json(payload).encode("utf-8")).hexdigest()
        signed_payload = payload | {
            "payload_sha256": payload_sha256,
            "signature_algorithm": "HMAC-SHA256",
        }
        signature = hmac.new(
            self.settings.certificate_signing_secret.encode("utf-8"),
            self._canonical_json(signed_payload).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return signed_payload | {"signature": signature}

    def to_pretty_json(self, certificate: dict[str, Any]) -> str:
        return json.dumps(certificate, default=self._json_value, indent=2, sort_keys=True) + "\n"

    def _get_run(self, demo_run_id: int) -> dict[str, Any]:
        self.repo.ensure_ui_tables()
        with self.conn.cursor() as cur:
            cur.execute("SELECT * FROM ml_ops.demo_ui_runs WHERE demo_run_id = %s", (demo_run_id,))
            run = cur.fetchone()
        if not run:
            raise CertificateNotFoundError("Demo run not found.")
        return run

    def _build_certificate_phases(self, run_row: dict[str, Any], state: DemoRunState) -> list[dict[str, Any]]:
        manual_records = self._manual_phase_records(run_row)
        phases_by_no = {phase.phase_no: phase for phase in state.phases}
        phase_numbers = sorted(set(phases_by_no) | set(manual_records))
        result: list[dict[str, Any]] = []

        for phase_no in phase_numbers:
            phase_state = phases_by_no.get(phase_no)
            manual_record = manual_records.get(phase_no)
            command_id = self._first_value(
                phase_state.command_id if phase_state else None,
                self._pick(manual_record, "command_id"),
            )
            command = self.repo.get_command(int(command_id)) if command_id is not None else None
            training_run_id = self._first_value(
                phase_state.training_run_id if phase_state else None,
                self._pick(manual_record, "training_run_id", "run_id", "final_training_run_id"),
                self._pick(command, "training_run_id", "run_id"),
            )
            location_name = str(
                self._first_value(
                    self._pick(manual_record, "location_name", "target_location_name"),
                    phase_state.location_name if phase_state else None,
                    self._pick(command, "target_location_name", "location_name"),
                    "unknown",
                )
            )
            region_code = str(
                self._first_value(
                    self._pick(manual_record, "region_code", "target_region_code"),
                    phase_state.region_code if phase_state else None,
                    self._pick(command, "target_region_code", "region_code"),
                    "unknown",
                )
            )
            output_checkpoint = self._first_value(
                phase_state.output_checkpoint_s3_uri if phase_state else None,
                self._pick(manual_record, "output_checkpoint_s3_uri", "final_checkpoint_s3_uri", "checkpoint_s3_uri"),
                self._extract_checkpoint(command),
            )
            if output_checkpoint is None and training_run_id is not None:
                output_checkpoint = self._derive_checkpoint_uri(region_code, location_name, training_run_id)

            metrics_row = self.repo.latest_metrics(
                int(command_id) if command_id is not None else None,
                int(training_run_id) if training_run_id is not None else None,
            )
            metrics = self._metrics_summary(metrics_row)
            command_status = self._first_value(
                self.repo.command_status(command) if command else None,
                phase_state.command_status if phase_state else None,
                self._pick(manual_record, "command_status", "status"),
            )

            result.append(
                {
                    "phase_no": phase_no,
                    "location_name": location_name,
                    "region_code": region_code,
                    "target_percent": self._first_value(
                        self._pick(manual_record, "target_percent"),
                        phase_state.target_percent if phase_state else None,
                    ),
                    "target_duration_seconds": self._first_value(
                        self._pick(manual_record, "target_duration_seconds"),
                        phase_state.target_duration_seconds if phase_state else None,
                    ),
                    "command_id": command_id,
                    "command_status": command_status,
                    "training_run_id": training_run_id,
                    "output_checkpoint_s3_uri": output_checkpoint,
                    "metrics": metrics,
                    "manual_phase_record": self._json_value(manual_record),
                    "command_details": self._command_details(command),
                }
            )

        return result

    def _manual_phase_records(self, run_row: dict[str, Any]) -> dict[int, dict[str, Any]]:
        if not table_exists(self.conn, "ml_ops", "manual_training_chain_phases"):
            return {}
        linked_chain_test_id = run_row.get("linked_chain_test_id")
        if linked_chain_test_id is None:
            return {}
        columns = get_columns(self.conn, "ml_ops", "manual_training_chain_phases")
        chain_col = first_existing(columns, ["chain_test_id", "manual_training_chain_test_id", "test_id"])
        phase_col = first_existing(columns, ["phase_no", "phase_number", "phase"])
        if not chain_col or not phase_col:
            return {}
        order_col = phase_col if phase_col in columns else first_existing(columns, ["created_at", "updated_at"])
        order_sql = sql.SQL("ORDER BY {} ASC").format(sql.Identifier(order_col)) if order_col else sql.SQL("")
        with self.conn.cursor() as cur:
            cur.execute(
                sql.SQL("SELECT * FROM ml_ops.manual_training_chain_phases WHERE {} = %s {}").format(
                    sql.Identifier(chain_col),
                    order_sql,
                ),
                (linked_chain_test_id,),
            )
            rows = cur.fetchall()
        result: dict[int, dict[str, Any]] = {}
        for row in rows:
            value = row.get(phase_col)
            if value is not None:
                result[int(value)] = row
        return result

    def _command_details(self, command: dict[str, Any] | None) -> dict[str, Any] | None:
        if not command:
            return None
        preferred_keys = [
            "command_id",
            "id",
            "command_type",
            "command_name",
            "command_status",
            "status",
            "target_location_name",
            "location_name",
            "target_region_code",
            "region_code",
            "model_id",
            "model_version",
            "phase_no",
            "target_percent",
            "target_duration_seconds",
            "training_run_id",
            "run_id",
            "resume_checkpoint_s3_uri",
            "output_checkpoint_s3_uri",
            "final_checkpoint_s3_uri",
            "checkpoint_s3_uri",
            "best_model_s3_uri",
            "created_at",
            "updated_at",
            "picked_up_at",
            "started_at",
            "finished_at",
            "command_payload",
            "payload",
            "parameters",
            "result_payload",
            "result",
            "metadata",
        ]
        details = {key: self._json_value(command[key]) for key in preferred_keys if key in command}
        for key, value in command.items():
            if key not in details:
                details[key] = self._json_value(value)
        return details

    def _metrics_summary(self, metrics_row: dict[str, Any] | None) -> dict[str, Any]:
        return {
            "map50": self._json_value(self._pick(metrics_row, "map50", "mAP50", "map_50")),
            "precision": self._json_value(self._pick(metrics_row, "precision")),
            "recall": self._json_value(self._pick(metrics_row, "recall")),
        }

    def _derive_checkpoint_uri(self, region_code: str, location_name: str, training_run_id: Any) -> str:
        location = re.sub(r"\s+", "_", location_name.strip())
        location = re.sub(r"[^A-Za-z0-9_.=-]", "_", location)
        return (
            f"s3://{self.settings.s3_bucket}/model-checkpoints/"
            f"{self.settings.demo_model_id}/{self.settings.demo_model_version}/"
            f"region_code={region_code}/location_name={location}/"
            f"run_id={training_run_id}/last_checkpoint/last.pt"
        )

    def _extract_checkpoint(self, command: dict[str, Any] | None) -> str | None:
        if not command:
            return None
        for key in ("output_checkpoint_s3_uri", "final_checkpoint_s3_uri", "checkpoint_s3_uri", "best_model_s3_uri"):
            value = command.get(key)
            if value:
                return str(value)
        for key in ("result_payload", "result", "metadata", "command_payload", "payload", "parameters"):
            value = command.get(key)
            if isinstance(value, dict):
                for nested_key in ("output_checkpoint_s3_uri", "final_checkpoint_s3_uri", "checkpoint_s3_uri", "best_model_s3_uri"):
                    if value.get(nested_key):
                        return str(value[nested_key])
        return None

    def _last_checkpoint(self, phases: list[dict[str, Any]]) -> str | None:
        for phase in reversed(phases):
            value = phase.get("output_checkpoint_s3_uri")
            if value:
                return str(value)
        return None

    def _canonical_json(self, payload: dict[str, Any]) -> str:
        return json.dumps(payload, default=self._json_value, sort_keys=True, separators=(",", ":"))

    def _pick(self, row: dict[str, Any] | None, *names: str) -> Any:
        if not row:
            return None
        for name in names:
            value = row.get(name)
            if value is not None:
                return value
        return None

    def _first_value(self, *values: Any) -> Any:
        for value in values:
            if value is not None:
                return value
        return None

    def _json_value(self, value: Any) -> Any:
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, DemoPhase):
            return value.model_dump(mode="json")
        if isinstance(value, dict):
            return {str(key): self._json_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._json_value(item) for item in value]
        return value
