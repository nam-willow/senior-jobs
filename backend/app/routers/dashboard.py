from __future__ import annotations
from datetime import date
from typing import Optional
from typing_extensions import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant import get_tenant_db
from app.core.permissions import CurrentUser, RequireTenantAdmin, get_current_user
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
async def get_summary(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
    year: Optional[int] = None,
):
    if year is None:
        year = date.today().year
    return await dashboard_service.get_summary(db, current_user.tenant_id, year)


@router.get("/kpi")
async def get_kpi(
    current_user: Annotated[CurrentUser, RequireTenantAdmin],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    return await dashboard_service.get_kpi(db, current_user.tenant_id)
