from typing_extensions import Annotated

from fastapi import APIRouter, Depends

from app.core.permissions import CurrentUser, Role, require_permission, require_role

router = APIRouter(prefix="/seniors", tags=["seniors"])


@router.get("/")
async def list_seniors(
    current_user: Annotated[CurrentUser, Depends(require_permission("VIEW_SENIOR"))],
):
    """Phase 1 stub — full implementation in Phase 2."""
    return {"items": [], "total": 0}


@router.post("/")
async def create_senior(
    current_user: Annotated[CurrentUser, Depends(require_role(Role.TENANT_ADMIN))],
):
    """Phase 1 stub — requires tenant_admin or higher."""
    return {"id": None}
