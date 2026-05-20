from __future__ import annotations
import uuid
from typing import Optional
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant import get_tenant_db
from app.core.permissions import CurrentUser, require_permission
from app.schemas.common import PaginatedResponse
from app.schemas.consultation_log import (
    ConsultationLogCreate,
    ConsultationLogResponse,
    ConsultationLogUpdate,
)
from app.services import consultation_log_service

router = APIRouter(prefix="/consultation-logs", tags=["consultation-logs"])


@router.get("/", response_model=PaginatedResponse[ConsultationLogResponse])
async def list_consultation_logs(
    current_user: Annotated[CurrentUser, Depends(require_permission("VIEW_SENIOR"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
    senior_id: Optional[str] = None,
):
    items = await consultation_log_service.list_consultation_logs(
        db, current_user.tenant_id, senior_id
    )
    return {"items": items, "total": len(items)}


@router.post("/", response_model=ConsultationLogResponse, status_code=status.HTTP_201_CREATED)
async def create_consultation_log(
    data: ConsultationLogCreate,
    request: Request,
    current_user: Annotated[CurrentUser, Depends(require_permission("EDIT_SENIOR"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    log = await consultation_log_service.create_consultation_log(
        db, current_user.tenant_id, current_user.user_id, data,
        ip_address=request.client.host if request.client else "unknown",
    )
    await db.commit()
    await db.refresh(log)
    return log


@router.put("/{log_id}", response_model=ConsultationLogResponse)
async def update_consultation_log(
    log_id: uuid.UUID,
    data: ConsultationLogUpdate,
    request: Request,
    current_user: Annotated[CurrentUser, Depends(require_permission("EDIT_SENIOR"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    log = await consultation_log_service.update_consultation_log(
        db, str(log_id), current_user.tenant_id, current_user.user_id, data,
        ip_address=request.client.host if request.client else "unknown",
    )
    await db.commit()
    await db.refresh(log)
    return log


@router.delete("/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_consultation_log(
    log_id: uuid.UUID,
    request: Request,
    current_user: Annotated[CurrentUser, Depends(require_permission("EDIT_SENIOR"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
):
    await consultation_log_service.delete_consultation_log(
        db, str(log_id), current_user.tenant_id, current_user.user_id,
        ip_address=request.client.host if request.client else "unknown",
    )
    await db.commit()
