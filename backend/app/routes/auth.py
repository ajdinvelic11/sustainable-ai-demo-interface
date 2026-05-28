from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.auth.session import clear_session_cookie, create_session, decode_session, set_session_cookie
from app.auth.vc_validator import CredentialValidationError, validate_vc_jwt
from app.config import Settings, get_settings
from app.schemas.auth import AuthConfigResponse, AuthResponse, AuthUser, LogoutResponse, VerifyRequest


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/config", response_model=AuthConfigResponse)
def auth_config(settings: Annotated[Settings, Depends(get_settings)]) -> AuthConfigResponse:
    return AuthConfigResponse(
        validation_enabled=settings.vc_jwt_validation_enabled,
        mock_mode=settings.vc_jwt_validation_mock_mode,
    )


@router.post("/verify", response_model=AuthResponse)
async def verify(request: VerifyRequest, response: Response, settings: Annotated[Settings, Depends(get_settings)]) -> AuthResponse:
    try:
        result = await validate_vc_jwt(request.token, settings)
    except CredentialValidationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    subject = result.claims.subject
    user = AuthUser(
        subject=subject,
        issuer=result.claims.issuer,
        credential_type=result.claims.credential_type,
        is_admin=subject in settings.app_admin_subjects,
        auth_mode=result.auth_mode,
    )
    token, csrf_token, expires_at = create_session(user, settings)
    set_session_cookie(response, settings, token)
    return AuthResponse(
        authenticated=True,
        user=user,
        csrf_token=csrf_token,
        demo_auth_mode=settings.mock_auth_visible,
        expires_at=expires_at,
    )


@router.get("/me", response_model=AuthResponse)
def me(request: Request, response: Response, settings: Annotated[Settings, Depends(get_settings)]) -> AuthResponse:
    # Decode from the cookie manually so frontend boot receives authenticated=false
    # instead of a hard 401 when no session exists.
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        clear_session_cookie(response, settings)
        return AuthResponse(authenticated=False, demo_auth_mode=settings.mock_auth_visible)
    decoded = decode_session(token, settings)
    if not decoded:
        clear_session_cookie(response, settings)
        return AuthResponse(authenticated=False, demo_auth_mode=settings.mock_auth_visible)
    user, csrf_token = decoded
    return AuthResponse(
        authenticated=True,
        user=user,
        csrf_token=csrf_token,
        demo_auth_mode=settings.mock_auth_visible,
    )


@router.post("/logout", response_model=LogoutResponse)
def logout(response: Response, settings: Annotated[Settings, Depends(get_settings)]) -> LogoutResponse:
    clear_session_cookie(response, settings)
    return LogoutResponse()
