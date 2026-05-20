from __future__ import annotations
import uuid
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant import get_tenant_db
from app.core.permissions import CurrentUser, RequirePlatform
from app.models.tenant import Tenant
from app.schemas.common import PaginatedResponse
from app.schemas.tenant import TenantCreate, TenantResponse, TenantUpdate

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.get("/", response_model=PaginatedResponse[TenantResponse])
async def list_tenants(
    current_user: Annotated[CurrentUser, RequirePlatform],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    result = await db.execute(select(Tenant).order_by(Tenant.created_at.desc()))
    items = list(result.scalars().all())
    return {"items": items, "total": len(items)}


@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    data: TenantCreate,
    current_user: Annotated[CurrentUser, RequirePlatform],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    tenant = Tenant(
        tenant_code=data.tenant_code,
        name=data.name,
        business_number=data.business_number,
        subscription_plan=data.subscription_plan,
    )
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return tenant


@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: uuid.UUID,
    data: TenantUpdate,
    current_user: Annotated[CurrentUser, RequirePlatform],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(tenant, field, value)
    await db.commit()
    await db.refresh(tenant)
    return tenant


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: uuid.UUID,
    current_user: Annotated[CurrentUser, RequirePlatform],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    tenant.is_active = False
    await db.commit()
