from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from typing_extensions import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant import get_tenant_db
from app.core.permissions import CurrentUser, require_permission
from app.models.audit_log import AuditLog
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


class AuditLogResponse:
    pass


from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    action_type: str
    target_table: str
    target_id: Optional[uuid.UUID]
    ip_address: str
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/", response_model=PaginatedResponse[AuditLogOut])
async def list_audit_logs(
    current_user: Annotated[CurrentUser, Depends(require_permission("VIEW_AUDIT_LOG"))],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
    target_table: Optional[str] = None,
    user_id: Optional[str] = None,
    from_dt: Optional[datetime] = None,
    to_dt: Optional[datetime] = None,
):
    q = select(AuditLog).where(
        AuditLog.tenant_id == uuid.UUID(current_user.tenant_id)
    ).execution_options(include_deleted=True)

    if target_table:
        q = q.where(AuditLog.target_table == target_table)
    if user_id:
        q = q.where(AuditLog.user_id == uuid.UUID(user_id))
    if from_dt:
        q = q.where(AuditLog.created_at >= from_dt)
    if to_dt:
        q = q.where(AuditLog.created_at <= to_dt)

    result = await db.execute(q.order_by(AuditLog.created_at.desc()).limit(200))
    items = list(result.scalars().all())
    return {"items": items, "total": len(items)}
