from __future__ import annotations
import uuid
from typing import Optional
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant import get_tenant_db
from app.core.permissions import CurrentUser, RequireTenantAdmin, require_permission
from app.schemas.business_unit import BusinessUnitCreate, BusinessUnitResponse, BusinessUnitUpdate
from app.schemas.common import PaginatedResponse
from app.services import business_unit_service

router = APIRouter(prefix="/business-units", tags=["business-units"])


@router.get("/", response_model=PaginatedResponse[BusinessUnitResponse])
async def list_business_units(
    current_user: Annotated[CurrentUser, Depends(require_permission("VIEW_SENIOR"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
    type: Optional[str] = None,
):
    items = await business_unit_service.list_business_units(db, current_user.tenant_id, type)
    return {"items": items, "total": len(items)}


@router.post("/", response_model=BusinessUnitResponse, status_code=status.HTTP_201_CREATED)
async def create_business_unit(
    data: BusinessUnitCreate,
    request: Request,
    current_user: Annotated[CurrentUser, RequireTenantAdmin],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    bu = await business_unit_service.create_business_unit(
        db, current_user.tenant_id, current_user.user_id, data
    )
    await db.commit()
    await db.refresh(bu)
    return bu


@router.put("/{bu_id}", response_model=BusinessUnitResponse)
async def update_business_unit(
    bu_id: uuid.UUID,
    data: BusinessUnitUpdate,
    current_user: Annotated[CurrentUser, RequireTenantAdmin],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    bu = await business_unit_service.update_business_unit(
        db, str(bu_id), current_user.tenant_id, data
    )
    await db.commit()
    await db.refresh(bu)
    return bu


@router.delete("/{bu_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_business_unit(
    bu_id: uuid.UUID,
    current_user: Annotated[CurrentUser, RequireTenantAdmin],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    await business_unit_service.delete_business_unit(db, str(bu_id), current_user.tenant_id)
    await db.commit()
