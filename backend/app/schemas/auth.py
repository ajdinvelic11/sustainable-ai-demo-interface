from datetime import datetime

from pydantic import BaseModel, Field


class VerifyRequest(BaseModel):
    token: str = Field(..., min_length=10, max_length=1_000_000)


class AuthUser(BaseModel):
    subject: str
    issuer: str
    credential_type: str
    is_admin: bool = False
    auth_mode: str = "validated"


class AuthResponse(BaseModel):
    authenticated: bool
    user: AuthUser | None = None
    csrf_token: str | None = None
    demo_auth_mode: bool = False
    expires_at: datetime | None = None


class AuthConfigResponse(BaseModel):
    validation_enabled: bool
    mock_mode: bool


class LogoutResponse(BaseModel):
    authenticated: bool = False
