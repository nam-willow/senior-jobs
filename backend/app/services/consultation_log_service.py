from __future__ import annotations
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.consultation_log import ConsultationLog
from app.models.senior import Senior
from app.schemas.consultation_log import ConsultationLogCreate, ConsultationLogUpdate
from app.services.audit import record_audit


async def create_consultation_log(
    db: AsyncSession, tenant_id: str, user_id: str, data: ConsultationLogCreate,
    ip_address: str, user_agent: str = "",
) -> ConsultationLog:
    senior_result = await db.execute(
        select(Senior).where(
            Senior.id == data.senior_id,
            Senior.tenant_id == uuid.UUID(tenant_id),
        )
    )
    if senior_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Senior not found")

    log = ConsultationLog(
        tenant_id=uuid.UUID(tenant_id),
        senior_id=data.senior_id,
        social_worker_id=uuid.UUID(user_id),
        consultation_date=data.consultation_date,
        method=data.method,
        content=data.content,
        memo=data.memo,
        default_session_hours=data.default_session_hours,
    )
    db.add(log)
    await db.flush()
    await record_audit(
        db, tenant_id=tenant_id, user_id=user_id,
        action_type="CREATE", target_table="consultation_logs",
        target_id=str(log.id),
        after_data={"senior_id": str(data.senior_id)},
        ip_address=ip_address, user_agent=user_agent,
    )
    await db.refresh(log)
    return log


async def get_consultation_log(
    db: AsyncSession, log_id: str, tenant_id: str
) -> ConsultationLog:
    result = await db.execute(
        select(ConsultationLog).where(
            ConsultationLog.id == uuid.UUID(log_id),
            ConsultationLog.tenant_id == uuid.UUID(tenant_id),
        )
    )
    log = result.scalar_one_or_none()
    if log is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation log not found")
    return log


async def list_consultation_logs(
    db: AsyncSession, tenant_id: str, senior_id: str | None = None
) -> list[ConsultationLog]:
    q = select(ConsultationLog).where(ConsultationLog.tenant_id == uuid.UUID(tenant_id))
    if senior_id:
        q = q.where(ConsultationLog.senior_id == uuid.UUID(senior_id))
    result = await db.execute(q.order_by(ConsultationLog.consultation_date.desc()))
    return list(result.scalars().all())


async def update_consultation_log(
    db: AsyncSession, log_id: str, tenant_id: str, user_id: str,
    data: ConsultationLogUpdate, ip_address: str, user_agent: str = "",
) -> ConsultationLog:
    log = await get_consultation_log(db, log_id, tenant_id)
    before = {"content": log.content, "method": log.method.value}
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(log, field, value)
    await record_audit(
        db, tenant_id=tenant_id, user_id=user_id,
        action_type="UPDATE", target_table="consultation_logs",
        target_id=log_id, before_data=before,
        after_data=data.model_dump(exclude_unset=True),
        ip_address=ip_address, user_agent=user_agent,
    )
    await db.flush()
    await db.refresh(log)
    return log


async def delete_consultation_log(
    db: AsyncSession, log_id: str, tenant_id: str, user_id: str,
    ip_address: str, user_agent: str = "",
) -> None:
    log = await get_consultation_log(db, log_id, tenant_id)
    log.soft_delete(uuid.UUID(user_id))
    await record_audit(
        db, tenant_id=tenant_id, user_id=user_id,
        action_type="DELETE", target_table="consultation_logs",
        target_id=log_id, ip_address=ip_address, user_agent=user_agent,
    )
    await db.flush()
