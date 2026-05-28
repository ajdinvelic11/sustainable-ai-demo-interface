from __future__ import annotations

from fastapi import Request

from app.auth.session import current_user_from_request
from app.config import Settings
from app.db import Database
from app.schemas.auth import SessionUser
from app.services.demo_orchestrator import DemoOrchestrator


def get_settings_from_app(request: Request) -> Settings:
    return request.app.state.settings


def get_db(request: Request) -> Database:
    return request.app.state.db


def get_orchestrator(request: Request) -> DemoOrchestrator:
    return request.app.state.orchestrator


def get_current_user(request: Request) -> SessionUser:
    return current_user_from_request(request.app.state.settings, request)

