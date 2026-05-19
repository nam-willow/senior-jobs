from __future__ import annotations
from typing import Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def record_audit(
    db: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
    action_type: str,
    target_table: str,
    ip_address: str,
    target_id: Optional[str] = None,
    before_data: Optional[dict] = None,
    after_data: Optional[dict] = None,
    user_agent: Optional[str] = None,
) -> None:
    db.add(AuditLog(
        tenant_id=uuid.UUID(tenant_id),
        user_id=uuid.UUID(user_id),
        action_type=action_type,
        target_table=target_table,
        target_id=uuid.UUID(target_id) if target_id else None,
        before_data=before_data,
        after_data=after_data,
        ip_address=ip_address,
        user_agent=user_agent,
    ))
    await db.flush()
