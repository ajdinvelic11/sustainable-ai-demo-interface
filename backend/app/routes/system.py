from typing import Annotated

from fastapi import APIRouter, Depends

from app.auth.dependencies import require_user
from app.config import Settings, get_settings
from app.schemas.auth import AuthUser
from app.schemas.demo import SiteInfo
from app.services.demo_repository import configured_sites


router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/sites", response_model=list[SiteInfo])
def sites(
    settings: Annotated[Settings, Depends(get_settings)],
    _: Annotated[AuthUser, Depends(require_user)],
) -> list[SiteInfo]:
    return configured_sites(settings)
