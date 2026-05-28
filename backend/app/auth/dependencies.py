from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from app.auth.session import decode_session
from app.config import Settings, get_settings
from app.schemas.auth import AuthUser


class AuthContext:
    def __init__(self, user: AuthUser, csrf_token: str):
        self.user = user
        self.csrf_token = csrf_token


def require_auth_context(request: Request, settings: Annotated[Settings, Depends(get_settings)]) -> AuthContext:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    decoded = decode_session(token, settings)
    if not decoded:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session.")
    user, csrf_token = decoded
    return AuthContext(user=user, csrf_token=csrf_token)


def require_user(context: Annotated[AuthContext, Depends(require_auth_context)]) -> AuthUser:
    return context.user


def require_admin(user: Annotated[AuthUser, Depends(require_user)]) -> AuthUser:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges are required.")
    return user


def require_csrf(
    context: Annotated[AuthContext, Depends(require_auth_context)],
    x_csrf_token: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> None:
    if not context.csrf_token or x_csrf_token != context.csrf_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token.")
