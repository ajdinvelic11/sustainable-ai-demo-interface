from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from typing import Any

import jwt
from fastapi import Response
from jwt import InvalidTokenError

from app.config import Settings
from app.schemas.auth import AuthUser


ALGORITHM = "HS256"


def create_session(user: AuthUser, settings: Settings) -> tuple[str, str, datetime]:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.app_session_ttl_minutes)
    csrf_token = token_urlsafe(32)
    payload: dict[str, Any] = {
        "sub": user.subject,
        "iss": settings.app_jwt_issuer,
        "aud": settings.app_jwt_audience,
        "credential_issuer": user.issuer,
        "credential_type": user.credential_type,
        "is_admin": user.is_admin,
        "auth_mode": user.auth_mode,
        "csrf": csrf_token,
        "exp": expires_at,
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, settings.app_jwt_secret, algorithm=ALGORITHM)
    return token, csrf_token, expires_at


def decode_session(token: str, settings: Settings) -> tuple[AuthUser, str] | None:
    try:
        payload = jwt.decode(
            token,
            settings.app_jwt_secret,
            algorithms=[ALGORITHM],
            issuer=settings.app_jwt_issuer,
            audience=settings.app_jwt_audience,
        )
    except InvalidTokenError:
        return None

    user = AuthUser(
        subject=str(payload.get("sub") or "unknown"),
        issuer=str(payload.get("credential_issuer") or "unknown"),
        credential_type=str(payload.get("credential_type") or "unknown"),
        is_admin=bool(payload.get("is_admin")),
        auth_mode=str(payload.get("auth_mode") or "validated"),
    )
    return user, str(payload.get("csrf") or "")


def set_session_cookie(response: Response, settings: Settings, token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.app_session_ttl_minutes * 60,
        path="/",
    )


def clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        secure=settings.cookie_secure,
        samesite="lax",
    )
