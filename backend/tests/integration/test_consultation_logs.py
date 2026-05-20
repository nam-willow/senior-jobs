"""
DI-CL-01~06: ConsultationLog domain integration tests
— CRUD + soft delete, real DB (senior_jobs_test).
"""
from __future__ import annotations
import uuid
from datetime import date, datetime, timezone

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business_unit import BusinessUnit, BusinessUnitType
from app.models.consultation_log import ConsultationLog, ConsultationMethod
from app.schemas.consultation_log import ConsultationLogCreate, ConsultationLogUpdate
from app.schemas.senior import SeniorCreate
from app.services.consultation_log_service import (
    create_consultation_log,
    delete_consultation_log,
    get_consultation_log,
    list_consultation_logs,
    update_consultation_log,
)
from app.services.senior_service import create_senior


IP = "127.0.0.1"


@pytest_asyncio.fixture
async def bu(db: AsyncSession, test_tenant_id: str):
    unit = BusinessUnit(
        tenant_id=uuid.UUID(test_tenant_id),
        name="상담일지 테스트 사업단",
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
async def senior(db, test_tenant_id, test_user, bu):
    return await create_senior(
        db, test_tenant_id, str(test_user.id),
        SeniorCreate(
            business_unit_id=bu.id,
            name="상담어르신",
            birth_date=date(1948, 6, 15),
            hourly_wage=10030,
            default_session_hours=3,
        ),
        IP,
    )


@pytest_asyncio.fixture
async def log_entry(db, test_tenant_id, test_user, senior):
    return await create_consultation_log(
        db, test_tenant_id, str(test_user.id),
        ConsultationLogCreate(
            senior_id=senior.id,
            consultation_date=datetime(2026, 3, 10, 10, 0, tzinfo=timezone.utc),
            method=ConsultationMethod.PHONE,
            content="초기 상담 내용",
            default_session_hours=3,
        ),
        IP,
    )


@pytest.mark.asyncio
async def test_di_cl_01_create_log(db, test_tenant_id, test_user, senior):
    """DI-CL-01: 상담일지 생성 — ID와 tenant_id 확인."""
    log = await create_consultation_log(
        db, test_tenant_id, str(test_user.id),
        ConsultationLogCreate(
            senior_id=senior.id,
            consultation_date=datetime(2026, 1, 15, 14, 0, tzinfo=timezone.utc),
            method=ConsultationMethod.VISIT,
            content="가정 방문 상담",
            default_session_hours=3,
        ),
        IP,
    )
    assert log.id is not None
    assert log.tenant_id == uuid.UUID(test_tenant_id)
    assert log.method == ConsultationMethod.VISIT


@pytest.mark.asyncio
async def test_di_cl_02_get_log(db, test_tenant_id, log_entry):
    """DI-CL-02: 상담일지 조회."""
    fetched = await get_consultation_log(db, str(log_entry.id), test_tenant_id)
    assert fetched.id == log_entry.id
    assert fetched.content == "초기 상담 내용"


@pytest.mark.asyncio
async def test_di_cl_03_get_log_wrong_tenant(db, log_entry):
    """DI-CL-03: 다른 tenant_id로 조회 시 404."""
    with pytest.raises(HTTPException) as exc_info:
        await get_consultation_log(db, str(log_entry.id), str(uuid.uuid4()))
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_di_cl_04_list_logs(db, test_tenant_id, test_user, log_entry, senior):
    """DI-CL-04: 목록 조회 — 생성한 항목 포함."""
    logs = await list_consultation_logs(db, test_tenant_id)
    ids = [str(l.id) for l in logs]
    assert str(log_entry.id) in ids


@pytest.mark.asyncio
async def test_di_cl_05_update_log(db, test_tenant_id, test_user, log_entry):
    """DI-CL-05: 내용 업데이트."""
    updated = await update_consultation_log(
        db, str(log_entry.id), test_tenant_id, str(test_user.id),
        ConsultationLogUpdate(content="수정된 상담 내용"),
        IP,
    )
    assert updated.content == "수정된 상담 내용"


@pytest.mark.asyncio
async def test_di_cl_06_soft_delete_log(db, test_tenant_id, test_user, log_entry):
    """DI-CL-06: soft delete → deleted_at 설정, 재조회 시 404."""
    await delete_consultation_log(db, str(log_entry.id), test_tenant_id, str(test_user.id), IP)

    result = await db.execute(
        select(ConsultationLog).where(ConsultationLog.id == log_entry.id)
        .execution_options(include_deleted=True)
    )
    row = result.scalar_one_or_none()
    assert row is not None
    assert row.deleted_at is not None

    with pytest.raises(HTTPException) as exc_info:
        await get_consultation_log(db, str(log_entry.id), test_tenant_id)
    assert exc_info.value.status_code == 404
