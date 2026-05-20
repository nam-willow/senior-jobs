from __future__ import annotations
import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.monthly_work_records import MonthlyWorkRecord, WorkRecordStatus
from app.models.senior import Senior
from app.schemas.work_record import MONTHLY_MAX_SOFT, WorkRecordCreate, WorkRecordUpdate
from app.services.audit import record_audit

MONTHLY_MAX_HARD = 43.0


async def create_work_record(
    db: AsyncSession,
    tenant_id: str,
    user_id: str,
    data: WorkRecordCreate,
    ip_address: str,
    user_agent: str = "",
) -> tuple[MonthlyWorkRecord, list[str]]:
    # 어르신 소속 테넌트 확인
    senior_result = await db.execute(
        select(Senior).where(
            Senior.id == data.senior_id,
            Senior.tenant_id == uuid.UUID(tenant_id),
        )
    )
    if senior_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Senior not found")

    warnings: list[str] = []
    if data.worked_hours > MONTHLY_MAX_SOFT:
        if not data.overtime_reason:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{MONTHLY_MAX_SOFT}시간 초과 시 overtime_reason 필수",
            )
        warnings.append(f"월 근무시간 {data.worked_hours}h — 초과 경고")

    record = MonthlyWorkRecord(
        tenant_id=uuid.UUID(tenant_id),
        senior_id=data.senior_id,
        year=data.year,
        month=data.month,
        worked_hours=data.worked_hours,
        worked_days=data.worked_days,
        amount_paid=data.amount_paid,
        overtime_reason=data.overtime_reason,
        created_by=uuid.UUID(user_id),
        status=WorkRecordStatus.DRAFT,
    )
    db.add(record)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="동일 연월 근무 기록이 이미 존재합니다",
        )

    await record_audit(
        db, tenant_id=tenant_id, user_id=user_id,
        action_type="CREATE", target_table="monthly_work_records",
        target_id=str(record.id),
        after_data={"year": data.year, "month": data.month, "worked_hours": data.worked_hours},
        ip_address=ip_address, user_agent=user_agent,
    )
    await db.refresh(record)
    return record, warnings


async def get_work_record(
    db: AsyncSession, record_id: str, tenant_id: str
) -> MonthlyWorkRecord:
    result = await db.execute(
        select(MonthlyWorkRecord).where(
            MonthlyWorkRecord.id == uuid.UUID(record_id),
            MonthlyWorkRecord.tenant_id == uuid.UUID(tenant_id),
        )
    )
    rec = result.scalar_one_or_none()
    if rec is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work record not found")
    return rec


async def list_work_records(
    db: AsyncSession,
    tenant_id: str,
    senior_id: Optional[str] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    record_status: Optional[str] = None,
) -> list[MonthlyWorkRecord]:
    q = select(MonthlyWorkRecord).where(
        MonthlyWorkRecord.tenant_id == uuid.UUID(tenant_id)
    )
    if senior_id:
        q = q.where(MonthlyWorkRecord.senior_id == uuid.UUID(senior_id))
    if year:
        q = q.where(MonthlyWorkRecord.year == year)
    if month:
        q = q.where(MonthlyWorkRecord.month == month)
    if record_status:
        q = q.where(MonthlyWorkRecord.status == record_status)
    result = await db.execute(q.order_by(MonthlyWorkRecord.year, MonthlyWorkRecord.month))
    return list(result.scalars().all())


async def update_work_record(
    db: AsyncSession,
    record_id: str,
    tenant_id: str,
    user_id: str,
    data: WorkRecordUpdate,
    ip_address: str,
    user_agent: str = "",
) -> tuple[MonthlyWorkRecord, list[str]]:
    rec = await get_work_record(db, record_id, tenant_id)
    if rec.status != WorkRecordStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="DRAFT 상태만 수정 가능",
        )

    warnings: list[str] = []
    update_data = data.model_dump(exclude_unset=True)
    new_hours = update_data.get("worked_hours", rec.worked_hours)

    if new_hours > MONTHLY_MAX_SOFT:
        if not (update_data.get("overtime_reason") or rec.overtime_reason):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{MONTHLY_MAX_SOFT}시간 초과 시 overtime_reason 필수",
            )
        warnings.append(f"월 근무시간 {new_hours}h — 초과 경고")

    before = {"worked_hours": float(rec.worked_hours), "worked_days": rec.worked_days}
    for field, value in update_data.items():
        setattr(rec, field, value)

    await record_audit(
        db, tenant_id=tenant_id, user_id=user_id,
        action_type="UPDATE", target_table="monthly_work_records",
        target_id=record_id, before_data=before, after_data=update_data,
        ip_address=ip_address, user_agent=user_agent,
    )
    await db.flush()
    await db.refresh(rec)
    return rec, warnings


async def submit_work_record(
    db: AsyncSession, record_id: str, tenant_id: str, user_id: str,
    ip_address: str, user_agent: str = "",
) -> MonthlyWorkRecord:
    rec = await get_work_record(db, record_id, tenant_id)
    if rec.status != WorkRecordStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="DRAFT 상태만 제출 가능",
        )
    rec.status = WorkRecordStatus.SUBMITTED
    await record_audit(
        db, tenant_id=tenant_id, user_id=user_id,
        action_type="UPDATE", target_table="monthly_work_records",
        target_id=record_id,
        before_data={"status": "DRAFT"}, after_data={"status": "SUBMITTED"},
        ip_address=ip_address, user_agent=user_agent,
    )
    await db.flush()
    await db.refresh(rec)
    return rec


async def approve_work_record(
    db: AsyncSession, record_id: str, tenant_id: str, user_id: str,
    ip_address: str, user_agent: str = "",
) -> MonthlyWorkRecord:
    from datetime import datetime, timezone
    rec = await get_work_record(db, record_id, tenant_id)
    if rec.status != WorkRecordStatus.SUBMITTED:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="SUBMITTED 상태만 승인 가능",
        )
    rec.status = WorkRecordStatus.APPROVED
    rec.approved_by = uuid.UUID(user_id)
    rec.approved_at = datetime.now(timezone.utc)
    await record_audit(
        db, tenant_id=tenant_id, user_id=user_id,
        action_type="UPDATE", target_table="monthly_work_records",
        target_id=record_id,
        before_data={"status": "SUBMITTED"}, after_data={"status": "APPROVED"},
        ip_address=ip_address, user_agent=user_agent,
    )
    await db.flush()
    await db.refresh(rec)
    return rec


async def reject_work_record(
    db: AsyncSession, record_id: str, tenant_id: str, user_id: str,
    reject_reason: str,
    ip_address: str, user_agent: str = "",
) -> MonthlyWorkRecord:
    rec = await get_work_record(db, record_id, tenant_id)
    if rec.status != WorkRecordStatus.SUBMITTED:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="SUBMITTED 상태만 반려 가능",
        )
    rec.status = WorkRecordStatus.REJECTED
    rec.reject_reason = reject_reason
    await record_audit(
        db, tenant_id=tenant_id, user_id=user_id,
        action_type="UPDATE", target_table="monthly_work_records",
        target_id=record_id,
        before_data={"status": "SUBMITTED"}, after_data={"status": "REJECTED"},
        ip_address=ip_address, user_agent=user_agent,
    )
    await db.flush()
    await db.refresh(rec)
    return rec


async def soft_delete_work_record(
    db: AsyncSession, record_id: str, tenant_id: str, user_id: str,
    ip_address: str, user_agent: str = "",
) -> None:
    rec = await get_work_record(db, record_id, tenant_id)
    rec.soft_delete(uuid.UUID(user_id))
    await record_audit(
        db, tenant_id=tenant_id, user_id=user_id,
        action_type="DELETE", target_table="monthly_work_records",
        target_id=record_id,
        ip_address=ip_address, user_agent=user_agent,
    )
    await db.flush()
