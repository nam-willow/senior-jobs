from __future__ import annotations
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.senior import Senior
from app.models.business_unit import BusinessUnit
from app.schemas.senior import SeniorCreate, SeniorUpdate
from app.services.audit import record_audit


async def create_senior(
    db: AsyncSession,
    tenant_id: str,
    user_id: str,
    data: SeniorCreate,
    ip_address: str,
    user_agent: str = "",
) -> Senior:
    # 사업단 존재 여부 확인
    bu_result = await db.execute(
        select(BusinessUnit).where(
            BusinessUnit.id == data.business_unit_id,
            BusinessUnit.tenant_id == uuid.UUID(tenant_id),
        )
    )
    bu = bu_result.scalar_one_or_none()
    if bu is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business unit not found")

    senior = Senior(
        tenant_id=uuid.UUID(tenant_id),
        business_unit_id=data.business_unit_id,
        name=data.name,
        birth_date=data.birth_date,
        workplace=data.workplace or "",
        allocated_hours=bu.total_annual_hours,
        hourly_wage=data.hourly_wage,
        default_session_hours=data.default_session_hours,
        notes=data.notes,
        created_by=uuid.UUID(user_id),
    )
    db.add(senior)
    await db.flush()

    await record_audit(
        db, tenant_id=tenant_id, user_id=user_id,
        action_type="CREATE", target_table="seniors",
        target_id=str(senior.id), after_data={"name": senior.name},
        ip_address=ip_address, user_agent=user_agent,
    )
    await db.refresh(senior)
    return senior


async def get_senior(db: AsyncSession, senior_id: str, tenant_id: str) -> Senior:
    result = await db.execute(
        select(Senior).where(
            Senior.id == uuid.UUID(senior_id),
            Senior.tenant_id == uuid.UUID(tenant_id),
        )
    )
    senior = result.scalar_one_or_none()
    if senior is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Senior not found")
    return senior


async def list_seniors(
    db: AsyncSession,
    tenant_id: str,
    business_unit_id: str | None = None,
    search: str | None = None,
) -> list[Senior]:
    q = select(Senior).where(Senior.tenant_id == uuid.UUID(tenant_id))
    if business_unit_id:
        q = q.where(Senior.business_unit_id == uuid.UUID(business_unit_id))
    if search:
        q = q.where(Senior.name.ilike(f"%{search}%"))
    result = await db.execute(q.order_by(Senior.created_at.desc()))
    return list(result.scalars().all())


async def update_senior(
    db: AsyncSession,
    senior_id: str,
    tenant_id: str,
    user_id: str,
    data: SeniorUpdate,
    ip_address: str,
    user_agent: str = "",
) -> Senior:
    senior = await get_senior(db, senior_id, tenant_id)
    before = {"name": senior.name, "hourly_wage": senior.hourly_wage}

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(senior, field, value)

    await record_audit(
        db, tenant_id=tenant_id, user_id=user_id,
        action_type="UPDATE", target_table="seniors",
        target_id=senior_id, before_data=before,
        after_data=data.model_dump(exclude_unset=True),
        ip_address=ip_address, user_agent=user_agent,
    )
    await db.flush()
    await db.refresh(senior)
    return senior


async def delete_senior(
    db: AsyncSession,
    senior_id: str,
    tenant_id: str,
    user_id: str,
    ip_address: str,
    user_agent: str = "",
) -> None:
    senior = await get_senior(db, senior_id, tenant_id)
    senior.soft_delete(uuid.UUID(user_id))
    await record_audit(
        db, tenant_id=tenant_id, user_id=user_id,
        action_type="DELETE", target_table="seniors",
        target_id=senior_id,
        ip_address=ip_address, user_agent=user_agent,
    )
    await db.flush()
