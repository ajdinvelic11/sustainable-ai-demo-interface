from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import HTTPException, Request, Response, status

from app.config import Settings
from app.schemas.auth import SessionUser


def create_session_token(settings: Settings, user_claims: dict[str, Any]) -> tuple[str, SessionUser]:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.session_ttl_minutes)
    roles = sorted(set(str(role) for role in user_claims.get("roles", []) if role))
    subject = str(user_claims.get("subject") or "unknown-subject")
    issuer = user_claims.get("issuer")
    is_admin = bool(user_claims.get("is_admin")) or subject in settings.app_admin_subjects

    payload = {
        "iss": settings.app_jwt_issuer,
        "aud": settings.app_jwt_audience,
        "sub": subject,
        "name": user_claims.get("name"),
        "email": user_claims.get("email"),
        "roles": roles,
        "is_admin": is_admin,
        "auth_mode": user_claims.get("auth_mode", "vc-jwt"),
        "external_issuer": issuer,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, settings.app_jwt_secret, algorithm="HS256")
    return token, session_user_from_payload(payload, expires_at)


def session_user_from_payload(payload: dict[str, Any], expires_at: datetime | None = None) -> SessionUser:
    exp = expires_at
    if exp is None:
        exp_value = payload.get("exp")
        exp = datetime.fromtimestamp(float(exp_value), tz=timezone.utc) if exp_value else datetime.now(timezone.utc)
    return SessionUser(
        subject=str(payload.get("sub")),
        issuer=payload.get("external_issuer"),
        name=payload.get("name"),
        email=payload.get("email"),
        roles=list(payload.get("roles") or []),
        is_admin=bool(payload.get("is_admin")),
        auth_mode=str(payload.get("auth_mode") or "vc-jwt"),
        expires_at=exp,
    )


def decode_session_token(settings: Settings, token: str) -> SessionUser:
    try:
        payload = jwt.decode(
            token,
            settings.app_jwt_secret,
            algorithms=["HS256"],
            audience=settings.app_jwt_audience,
            issuer=settings.app_jwt_issuer,
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session") from exc
    return session_user_from_payload(payload)


def set_session_cookie(settings: Settings, response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_ttl_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(settings: Settings, response: Response) -> None:
    response.delete_cookie(key=settings.session_cookie_name, path="/", samesite="lax")


def current_user_from_request(settings: Settings, request: Request) -> SessionUser:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        authorization = request.headers.get("authorization", "")
        if authorization.lower().startswith("bearer "):
            token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return decode_session_token(settings, token)


def require_admin(user: SessionUser) -> None:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

