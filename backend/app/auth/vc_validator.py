import base64
import hashlib
import json
import logging
import re
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import Settings


logger = logging.getLogger(__name__)
JWT_RE = re.compile(r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$")


class CredentialValidationError(Exception):
    pass


@dataclass
class CredentialClaims:
    subject: str
    issuer: str
    credential_type: str
    raw_types: list[str]


@dataclass
class CredentialValidationResult:
    valid: bool
    claims: CredentialClaims
    auth_mode: str
    response_status: int | None = None
    credential_hash: str | None = None


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def looks_like_jwt(token: str) -> bool:
    return bool(JWT_RE.fullmatch(token.strip()))


def _b64_json(segment: str) -> dict[str, Any]:
    try:
        padding = "=" * (-len(segment) % 4)
        return json.loads(base64.urlsafe_b64decode(f"{segment}{padding}".encode("utf-8")))
    except Exception:
        return {}


def decode_unverified_claims(token: str) -> CredentialClaims:
    payload = _b64_json(token.split(".")[1]) if token.count(".") >= 2 else {}
    vc = payload.get("vc") if isinstance(payload.get("vc"), dict) else payload
    subject_obj = vc.get("credentialSubject") if isinstance(vc.get("credentialSubject"), dict) else {}
    raw_type = vc.get("type") or payload.get("type")
    if isinstance(raw_type, list):
        types = [str(item) for item in raw_type if item is not None]
    elif raw_type:
        types = [str(raw_type)]
    else:
        types = []
    subject = str(payload.get("sub") or subject_obj.get("id") or subject_obj.get("@id") or "unknown")
    issuer = str(payload.get("iss") or vc.get("issuer") or "unknown")
    credential_type = ", ".join(types) if types else "unknown"
    return CredentialClaims(subject=subject, issuer=issuer, credential_type=credential_type, raw_types=types)


def _field_path(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _is_compliant_response(response: httpx.Response, expected_field: str) -> bool:
    if response.status_code < 200 or response.status_code >= 300:
        return False
    if not response.text.strip():
        return True
    content_type = response.headers.get("content-type", "")
    if "json" not in content_type:
        return True
    try:
        data = response.json()
    except ValueError:
        return True
    if isinstance(data, bool):
        return data
    if isinstance(data, dict):
        configured_value = _field_path(data, expected_field)
        if configured_value is not None:
            return bool(configured_value)
        for fallback in ("compliant", "valid", "verified", "success"):
            value = _field_path(data, fallback)
            if value is not None:
                return bool(value)
    return True


async def validate_vc_jwt(token: str, settings: Settings) -> CredentialValidationResult:
    raw_token = token.strip()
    token_hash = hash_token(raw_token)
    if not looks_like_jwt(raw_token):
        raise CredentialValidationError("Token must be a JWT / VC-JWT with three dot-separated parts.")

    claims = decode_unverified_claims(raw_token)

    if settings.vc_jwt_validation_mock_mode:
        logger.warning("VC-JWT validation is running in MOCK MODE", extra={"token_hash_prefix": token_hash[:12]})
        return CredentialValidationResult(
            valid=True,
            claims=claims,
            auth_mode="mock",
            response_status=None,
            credential_hash=token_hash,
        )

    if not settings.vc_jwt_validation_enabled:
        raise CredentialValidationError("VC-JWT validation is disabled and mock mode is not enabled.")

    try:
        async with httpx.AsyncClient(timeout=settings.vc_jwt_validation_timeout_seconds) as client:
            response = await client.post(
                settings.vc_jwt_validation_url,
                content=raw_token,
                headers={"Content-Type": "application/vc+jwt", "Accept": "application/json, application/vc+jwt, */*"},
            )
    except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPError) as exc:
        logger.warning("VC-JWT verifier call failed", extra={"error": str(exc), "token_hash_prefix": token_hash[:12]})
        raise CredentialValidationError("VC-JWT validation service is not reachable.") from exc

    if not _is_compliant_response(response, settings.vc_jwt_validation_expected_compliant_field):
        logger.info(
            "VC-JWT verifier rejected token",
            extra={"status_code": response.status_code, "token_hash_prefix": token_hash[:12]},
        )
        raise CredentialValidationError("VC-JWT validation failed.")

    return CredentialValidationResult(
        valid=True,
        claims=claims,
        auth_mode="validated",
        response_status=response.status_code,
        credential_hash=token_hash,
    )
