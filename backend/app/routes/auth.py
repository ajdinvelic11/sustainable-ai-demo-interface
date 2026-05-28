from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.auth.session import clear_session_cookie, create_session_token, current_user_from_request, set_session_cookie
from app.auth.vc_jwt import VcJwtValidationAdapter, claims_to_session_identity
from app.config import Settings
from app.routes.dependencies import get_settings_from_app
from app.schemas.auth import AuthConfigResponse, AuthResponse, MeResponse, VerifyTokenRequest

router = APIRouter(prefix="/api/auth", tags=["authentication"])


@router.get("/config", response_model=AuthConfigResponse)
def auth_config(settings: Settings = Depends(get_settings_from_app)) -> AuthConfigResponse:
    return AuthConfigResponse(
        validation_enabled=settings.vc_jwt_validation_enabled,
        mock_mode=settings.vc_jwt_validation_mock_mode,
        validation_url_configured=bool(settings.vc_jwt_validation_url and "CHANGE_ME" not in settings.vc_jwt_validation_url),
    )


@router.post("/verify", response_model=AuthResponse)
async def verify_token(
    payload: VerifyTokenRequest,
    response: Response,
    settings: Settings = Depends(get_settings_from_app),
) -> AuthResponse:
    if settings.is_production and settings.app_jwt_secret == "change-me":
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="APP_JWT_SECRET must be changed in production.")

    adapter = VcJwtValidationAdapter(settings)
    result = await adapter.verify(payload.token.strip())
    if not result.compliant:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=result.message)

    identity = claims_to_session_identity(
        settings,
        result.claims,
        "mock" if settings.vc_jwt_validation_mock_mode else "vc-jwt",
    )
    token, user = create_session_token(settings, identity)
    set_session_cookie(settings, response, token)
    return AuthResponse(
        authenticated=True,
        user=user,
        demo_auth_mode=settings.vc_jwt_validation_mock_mode,
        message=result.message,
    )


@router.post("/logout")
def logout(response: Response, settings: Settings = Depends(get_settings_from_app)) -> dict[str, bool]:
    clear_session_cookie(settings, response)
    return {"ok": True}


@router.get("/me", response_model=MeResponse)
def me(request: Request, settings: Settings = Depends(get_settings_from_app)) -> MeResponse:
    try:
        user = current_user_from_request(settings, request)
    except HTTPException:
        return MeResponse(authenticated=False, user=None, demo_auth_mode=settings.vc_jwt_validation_mock_mode)
    return MeResponse(authenticated=True, user=user, demo_auth_mode=settings.vc_jwt_validation_mock_mode)

