from __future__ import annotations
import uuid
from typing import Optional
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant import get_tenant_db
from app.core.permissions import CurrentUser, require_permission
from app.schemas.common import PaginatedResponse
from app.schemas.senior import SeniorCreate, SeniorResponse, SeniorUpdate
from app.services import senior_service

router = APIRouter(prefix="/seniors", tags=["seniors"])


@router.get("/", response_model=PaginatedResponse[SeniorResponse])
async def list_seniors(
    current_user: Annotated[CurrentUser, Depends(require_permission("VIEW_SENIOR"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
    business_unit_id: Optional[str] = None,
    search: Optional[str] = None,
):
    items = await senior_service.list_seniors(
        db, current_user.tenant_id, business_unit_id, search
    )
    return {"items": items, "total": len(items)}


@router.post("/", response_model=SeniorResponse, status_code=status.HTTP_201_CREATED)
async def create_senior(
    data: SeniorCreate,
    request: Request,
    current_user: Annotated[CurrentUser, Depends(require_permission("EDIT_SENIOR"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    senior = await senior_service.create_senior(
        db, current_user.tenant_id, current_user.user_id, data,
        ip_address=request.client.host if request.client else "unknown",
    )
    await db.commit()
    await db.refresh(senior)
    return senior


@router.get("/{senior_id}", response_model=SeniorResponse)
async def get_senior(
    senior_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(require_permission("VIEW_SENIOR"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    return await senior_service.get_senior(db, str(senior_id), current_user.tenant_id)


@router.put("/{senior_id}", response_model=SeniorResponse)
async def update_senior(
    senior_id: uuid.UUID,
    data: SeniorUpdate,
    request: Request,
    current_user: Annotated[CurrentUser, Depends(require_permission("EDIT_SENIOR"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    senior = await senior_service.update_senior(
        db, str(senior_id), current_user.tenant_id, current_user.user_id, data,
        ip_address=request.client.host if request.client else "unknown",
    )
    await db.commit()
    await db.refresh(senior)
    return senior


@router.delete("/{senior_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_senior(
    senior_id: uuid.UUID,
    request: Request,
    current_user: Annotated[CurrentUser, Depends(require_permission("DELETE_SENIOR"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    await senior_service.delete_senior(
        db, str(senior_id), current_user.tenant_id, current_user.user_id,
        ip_address=request.client.host if request.client else "unknown",
    )
    await db.commit()
