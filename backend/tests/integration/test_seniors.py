"""
DI-SR-01~06: Senior domain integration tests
— CRUD + soft delete, real DB (senior_jobs_test).
"""
from __future__ import annotations
import uuid
from datetime import date

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business_unit import BusinessUnit, BusinessUnitType
from app.models.senior import Senior
from app.schemas.senior import SeniorCreate, SeniorUpdate
from app.services.senior_service import (
    create_senior,
    delete_senior,
    get_senior,
    list_seniors,
    update_senior,
)


IP = "127.0.0.1"


@pytest_asyncio.fixture
async def bu(db: AsyncSession, test_tenant_id: str) -> BusinessUnit:
    unit = BusinessUnit(
        tenant_id=uuid.UUID(test_tenant_id),
        name="통합테스트 사업단",
        type=BusinessUnitType.PUBLIC_BENEFIT,
        year=2026,
        monthly_default_hours=30,
        monthly_max_hours=42,
        total_annual_hours=330,
        session_default_hours=3,
        session_max_hours=4,
        is_active=True,
    )
    db.add(unit)
    await db.flush()
    return unit


@pytest_asyncio.fixture
async def senior(db: AsyncSession, test_tenant_id: str, test_user, bu: BusinessUnit) -> Senior:
    data = SeniorCreate(
        business_unit_id=bu.id,
        name="홍길동",
        birth_date=date(1950, 1, 1),
        hourly_wage=10030,
        default_session_hours=3,
    )
    return await create_senior(
        db, tenant_id=test_tenant_id, user_id=str(test_user.id),
        data=data, ip_address=IP,
    )


@pytest.mark.asyncio
async def test_di_sr_01_create_senior(db, test_tenant_id, test_user, bu):
    """DI-SR-01: senior 생성 — allocated_hours가 BU.total_annual_hours와 일치."""
    data = SeniorCreate(
        business_unit_id=bu.id,
        name="이순신",
        birth_date=date(1945, 4, 28),
        hourly_wage=10030,
        default_session_hours=3,
    )
    s = await create_senior(db, test_tenant_id, str(test_user.id), data, IP)
    assert s.id is not None
    assert s.allocated_hours == bu.total_annual_hours
    assert s.tenant_id == uuid.UUID(test_tenant_id)


@pytest.mark.asyncio
async def test_di_sr_02_get_senior(db, test_tenant_id, senior):
    """DI-SR-02: senior 조회 — ID와 tenant_id로 정확히 반환."""
    fetched = await get_senior(db, str(senior.id), test_tenant_id)
    assert fetched.id == senior.id
    assert fetched.name == "홍길동"


@pytest.mark.asyncio
async def test_di_sr_03_get_senior_wrong_tenant_raises(db, senior):
    """DI-SR-03: 다른 tenant_id로 조회 시 404."""
    with pytest.raises(HTTPException) as exc_info:
        await get_senior(db, str(senior.id), str(uuid.uuid4()))
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_di_sr_04_list_seniors(db, test_tenant_id, test_user, senior, bu):
    """DI-SR-04: list_seniors — 생성한 senior가 목록에 포함."""
    seniors = await list_seniors(db, test_tenant_id)
    ids = [str(s.id) for s in seniors]
    assert str(senior.id) in ids


@pytest.mark.asyncio
async def test_di_sr_05_update_senior(db, test_tenant_id, test_user, senior):
    """DI-SR-05: senior 업데이트 — 이름 변경 확인."""
    data = SeniorUpdate(name="박문수")
    updated = await update_senior(db, str(senior.id), test_tenant_id, str(test_user.id), data, IP)
    assert updated.name == "박문수"


@pytest.mark.asyncio
async def test_di_sr_06_soft_delete_senior(db, test_tenant_id, test_user, senior):
    """DI-SR-06: soft delete — deleted_at이 채워지고 재조회 시 404."""
    await delete_senior(db, str(senior.id), test_tenant_id, str(test_user.id), IP)

    # 직접 SELECT (soft delete 필터 우회)
    result = await db.execute(
        select(Senior).where(Senior.id == senior.id).execution_options(include_deleted=True)
    )
    row = result.scalar_one_or_none()
    assert row is not None
    assert row.deleted_at is not None

    # 서비스 조회는 404
    with pytest.raises(HTTPException) as exc_info:
        await get_senior(db, str(senior.id), test_tenant_id)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_di_sr_07_create_senior_unknown_bu(db, test_tenant_id, test_user):
    """DI-SR-07: 존재하지 않는 business_unit_id → 404."""
    data = SeniorCreate(
        business_unit_id=uuid.uuid4(),
        name="유령",
        birth_date=date(1960, 1, 1),
        hourly_wage=10030,
        default_session_hours=3,
    )
    with pytest.raises(HTTPException) as exc_info:
        await create_senior(db, test_tenant_id, str(test_user.id), data, IP)
    assert exc_info.value.status_code == 404
