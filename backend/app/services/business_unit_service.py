from __future__ import annotations
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business_unit import BusinessUnit, BusinessUnitType
from app.schemas.business_unit import BusinessUnitCreate, BusinessUnitUpdate, TYPE_DEFAULTS


async def create_business_unit(
    db: AsyncSession,
    tenant_id: str,
    user_id: str,
    data: BusinessUnitCreate,
) -> BusinessUnit:
    # 공익/사회서비스형은 정책 기준 자동 적용 (수동 입력 무시)
    if data.type != BusinessUnitType.MARKET:
        defaults = TYPE_DEFAULTS[data.type.value]
        bu = BusinessUnit(
            tenant_id=uuid.UUID(tenant_id),
            name=data.name,
            type=data.type,
            year=data.year,
            description=data.description,
            **defaults,
        )
    else:
        bu = BusinessUnit(
            tenant_id=uuid.UUID(tenant_id),
            name=data.name,
            type=data.type,
            year=data.year,
            description=data.description,
            monthly_default_hours=data.monthly_default_hours,
            monthly_max_hours=data.monthly_max_hours,
            total_annual_hours=data.total_annual_hours,
            session_default_hours=data.session_default_hours,
            session_max_hours=8,  # 시장형 고정
            carry_over_enabled=False,
        )
    db.add(bu)
    await db.flush()
    await db.refresh(bu)
    return bu


async def get_business_unit(
    db: AsyncSession, bu_id: str, tenant_id: str
) -> BusinessUnit:
    result = await db.execute(
        select(BusinessUnit).where(
            BusinessUnit.id == uuid.UUID(bu_id),
            BusinessUnit.tenant_id == uuid.UUID(tenant_id),
        )
    )
    bu = result.scalar_one_or_none()
    if bu is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business unit not found")
    return bu


async def list_business_units(
    db: AsyncSession, tenant_id: str, type_filter: str | None = None
) -> list[BusinessUnit]:
    q = select(BusinessUnit).where(BusinessUnit.tenant_id == uuid.UUID(tenant_id))
    if type_filter:
        q = q.where(BusinessUnit.type == type_filter)
    result = await db.execute(q.order_by(BusinessUnit.created_at.desc()))
    return list(result.scalars().all())


async def update_business_unit(
    db: AsyncSession,
    bu_id: str,
    tenant_id: str,
    data: BusinessUnitUpdate,
) -> BusinessUnit:
    bu = await get_business_unit(db, bu_id, tenant_id)
    update_data = data.model_dump(exclude_unset=True)

    # 공익/사회서비스형은 시간 항목 수정 불가
    if bu.type != BusinessUnitType.MARKET:
        for field in ["monthly_default_hours", "monthly_max_hours",
                      "total_annual_hours", "session_default_hours"]:
            update_data.pop(field, None)

    for field, value in update_data.items():
        setattr(bu, field, value)

    await db.flush()
    await db.refresh(bu)
    return bu


async def delete_business_unit(db: AsyncSession, bu_id: str, tenant_id: str) -> None:
    bu = await get_business_unit(db, bu_id, tenant_id)
    bu.is_active = False
    await db.flush()
