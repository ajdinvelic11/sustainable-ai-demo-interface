from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    compliant: bool
    claims: dict[str, Any]
    message: str
    raw_response: dict[str, Any] | None = None


def _decode_segment(segment: str) -> dict[str, Any]:
    padding = "=" * (-len(segment) % 4)
    data = base64.urlsafe_b64decode((segment + padding).encode("ascii"))
    return json.loads(data.decode("utf-8"))


def decode_unverified_jwt(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) < 2:
        return {}
    try:
        return _decode_segment(parts[1])
    except Exception:
        return {}


def _value_at_path(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def _extract_roles(claims: dict[str, Any]) -> list[str]:
    candidates = [
        claims.get("roles"),
        claims.get("role"),
        claims.get("groups"),
        claims.get("scope"),
        _value_at_path(claims, "credentialSubject.roles"),
    ]
    roles: list[str] = []
    for candidate in candidates:
        if isinstance(candidate, str):
            roles.extend([item for item in candidate.replace(",", " ").split(" ") if item])
        elif isinstance(candidate, list):
            roles.extend([str(item) for item in candidate if item])
    return sorted(set(roles))


def claims_to_session_identity(settings: Settings, claims: dict[str, Any], auth_mode: str) -> dict[str, Any]:
    subject = (
        claims.get("sub")
        or _value_at_path(claims, "credentialSubject.id")
        or claims.get("id")
        or claims.get("issuer")
        or claims.get("iss")
        or ("demo-admin" if auth_mode == "mock" else None)
    )
    roles = _extract_roles(claims)
    is_admin = bool(set(roles).intersection({"admin", "administrator", "demo-admin"}))
    if subject in settings.app_admin_subjects:
        is_admin = True
    if auth_mode == "mock":
        is_admin = True
    return {
        "subject": str(subject or "vc-jwt-user"),
        "issuer": claims.get("iss") or claims.get("issuer"),
        "name": claims.get("name") or _value_at_path(claims, "credentialSubject.name"),
        "email": claims.get("email") or _value_at_path(claims, "credentialSubject.email"),
        "roles": roles,
        "is_admin": is_admin,
        "auth_mode": auth_mode,
    }


class VcJwtValidationAdapter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def verify(self, token: str) -> ValidationResult:
        claims = decode_unverified_jwt(token)
        if self.settings.vc_jwt_validation_mock_mode:
            logger.warning("vc_jwt_mock_mode_enabled")
            return ValidationResult(
                compliant=True,
                claims=claims or {"sub": "demo-admin", "roles": ["demo-admin"]},
                message="Demo Auth Mode accepted token without external validation.",
                raw_response={"mock_mode": True},
            )

        if not self.settings.vc_jwt_validation_enabled:
            return ValidationResult(
                compliant=False,
                claims=claims,
                message="VC-JWT validation is disabled and mock mode is off.",
            )

        if "CHANGE_ME" in self.settings.vc_jwt_validation_url:
            return ValidationResult(
                compliant=False,
                claims=claims,
                message="VC-JWT validation URL is not configured.",
            )

        headers = {
            "accept": "application/json",
            "content-type": self.settings.vc_jwt_validation_content_type,
        }
        try:
            async with httpx.AsyncClient(timeout=self.settings.vc_jwt_validation_timeout_seconds) as client:
                response = await client.post(self.settings.vc_jwt_validation_url, content=token, headers=headers)
        except httpx.HTTPError as exc:
            logger.warning("vc_jwt_validation_request_failed", extra={"_error": str(exc)})
            return ValidationResult(compliant=False, claims=claims, message=f"Validation request failed: {exc}")

        raw: dict[str, Any] | None = None
        if response.content:
            try:
                parsed = response.json()
                if isinstance(parsed, dict):
                    raw = parsed
            except ValueError:
                raw = {"body": response.text[:1000]}

        if response.status_code < 200 or response.status_code >= 300:
            return ValidationResult(
                compliant=False,
                claims=claims,
                message=f"External validation rejected token with HTTP {response.status_code}.",
                raw_response=raw,
            )

        expected_field = self.settings.vc_jwt_validation_expected_compliant_field
        if raw and expected_field:
            value = _value_at_path(raw, expected_field)
            if value is not None and value is not True:
                return ValidationResult(
                    compliant=False,
                    claims=claims,
                    message=f"Validation response field '{expected_field}' is not compliant.",
                    raw_response=raw,
                )

        return ValidationResult(
            compliant=True,
            claims=claims,
            message="VC-JWT validation succeeded.",
            raw_response=raw,
        )

