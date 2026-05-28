from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class VerifyTokenRequest(BaseModel):
    token: str = Field(min_length=16)


class AuthConfigResponse(BaseModel):
    validation_enabled: bool
    mock_mode: bool
    validation_url_configured: bool


class SessionUser(BaseModel):
    subject: str
    issuer: str | None = None
    name: str | None = None
    email: str | None = None
    roles: list[str] = []
    is_admin: bool = False
    auth_mode: str
    expires_at: datetime


class AuthResponse(BaseModel):
    authenticated: bool
    user: SessionUser
    demo_auth_mode: bool = False
    message: str


class MeResponse(BaseModel):
    authenticated: bool
    user: SessionUser | None = None
    demo_auth_mode: bool = False

