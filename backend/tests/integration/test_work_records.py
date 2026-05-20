"""
DI-WR-01~09: WorkRecord domain integration tests
— DRAFT→SUBMITTED→APPROVED/REJECTED 상태기계, 42h 버퍼, soft delete, 중복 생성.
"""
from __future__ import annotations
import uuid
from datetime import date

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business_unit import BusinessUnit, BusinessUnitType
from app.models.monthly_work_records import WorkRecordStatus
from app.schemas.senior import SeniorCreate
from app.schemas.work_record import WorkRecordCreate, WorkRecordUpdate
from app.services.senior_service import create_senior
from app.services.work_record_service import (
    approve_work_record,
    create_work_record,
    get_work_record,
    reject_work_record,
    soft_delete_work_record,
    submit_work_record,
    update_work_record,
)


IP = "127.0.0.1"


@pytest_asyncio.fixture
async def bu(db: AsyncSession, test_tenant_id: str):
    unit = BusinessUnit(
        tenant_id=uuid.UUID(test_tenant_id),
        name="WR 테스트 사업단",
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
            name="WR어르신",
            birth_date=date(1950, 3, 15),
            hourly_wage=10030,
            default_session_hours=3,
        ),
        IP,
    )


@pytest_asyncio.fixture
async def draft_record(db, test_tenant_id, test_user, senior):
    rec, _ = await create_work_record(
        db, test_tenant_id, str(test_user.id),
        WorkRecordCreate(
            senior_id=senior.id,
            year=2026,
            month=3,
            worked_hours=40.0,
            worked_days=20,
            amount_paid=400300,
        ),
        IP,
    )
    return rec


@pytest.mark.asyncio
async def test_di_wr_01_create_draft(db, test_tenant_id, test_user, senior):
    """DI-WR-01: 근무기록 생성 → DRAFT 상태."""
    rec, warnings = await create_work_record(
        db, test_tenant_id, str(test_user.id),
        WorkRecordCreate(
            senior_id=senior.id, year=2026, month=1,
            worked_hours=30.0, worked_days=15, amount_paid=300900,
        ),
        IP,
    )
    assert rec.status == WorkRecordStatus.DRAFT
    assert rec.id is not None
    assert warnings == []


@pytest.mark.asyncio
async def test_di_wr_02_42h_soft_warning(db, test_tenant_id, test_user, senior):
    """DI-WR-02: 42.5h 입력 → warnings 반환, DRAFT 생성."""
    rec, warnings = await create_work_record(
        db, test_tenant_id, str(test_user.id),
        WorkRecordCreate(
            senior_id=senior.id, year=2026, month=2,
            worked_hours=42.5, worked_days=21, amount_paid=426273,
            overtime_reason="불가피한 초과",
        ),
        IP,
    )
    assert rec.status == WorkRecordStatus.DRAFT
    assert len(warnings) == 1
    assert "초과 경고" in warnings[0]


@pytest.mark.asyncio
async def test_di_wr_03_43h_hard_limit(db, test_tenant_id, test_user, senior):
    """DI-WR-03: 43.5h 입력 → 422 (스키마 하드 제한)."""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        WorkRecordCreate(
            senior_id=senior.id, year=2026, month=4,
            worked_hours=43.5, worked_days=22, amount_paid=436307,
            overtime_reason="하드 초과",
        )


@pytest.mark.asyncio
async def test_di_wr_04_submit(db, test_tenant_id, test_user, draft_record):
    """DI-WR-04: DRAFT → SUBMITTED."""
    rec = await submit_work_record(
        db, str(draft_record.id), test_tenant_id, str(test_user.id), IP
    )
    assert rec.status == WorkRecordStatus.SUBMITTED


@pytest.mark.asyncio
async def test_di_wr_05_approve(db, test_tenant_id, test_user, draft_record):
    """DI-WR-05: SUBMITTED → APPROVED, approved_by 채워짐."""
    await submit_work_record(db, str(draft_record.id), test_tenant_id, str(test_user.id), IP)
    rec = await approve_work_record(db, str(draft_record.id), test_tenant_id, str(test_user.id), IP)
    assert rec.status == WorkRecordStatus.APPROVED
    assert rec.approved_by == test_user.id
    assert rec.approved_at is not None


@pytest.mark.asyncio
async def test_di_wr_06_reject(db, test_tenant_id, test_user, senior):
    """DI-WR-06: SUBMITTED → REJECTED, reject_reason 채워짐."""
    rec, _ = await create_work_record(
        db, test_tenant_id, str(test_user.id),
        WorkRecordCreate(
            senior_id=senior.id, year=2026, month=5,
            worked_hours=35.0, worked_days=17, amount_paid=351050,
        ),
        IP,
    )
    await submit_work_record(db, str(rec.id), test_tenant_id, str(test_user.id), IP)
    rejected = await reject_work_record(
        db, str(rec.id), test_tenant_id, str(test_user.id),
        reject_reason="서류 오류", ip_address=IP,
    )
    assert rejected.status == WorkRecordStatus.REJECTED
    assert rejected.reject_reason == "서류 오류"


@pytest.mark.asyncio
async def test_di_wr_07_edit_non_draft_raises(db, test_tenant_id, test_user, draft_record):
    """DI-WR-07: SUBMITTED 상태 수정 시도 → 422."""
    await submit_work_record(db, str(draft_record.id), test_tenant_id, str(test_user.id), IP)
    with pytest.raises(HTTPException) as exc_info:
        await update_work_record(
            db, str(draft_record.id), test_tenant_id, str(test_user.id),
            WorkRecordUpdate(worked_hours=20.0), IP,
        )
    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_di_wr_08_soft_delete_draft(db, test_tenant_id, test_user, draft_record):
    """DI-WR-08: soft delete → 재조회 404."""
    await soft_delete_work_record(db, str(draft_record.id), test_tenant_id, str(test_user.id), IP)
    with pytest.raises(HTTPException) as exc_info:
        await get_work_record(db, str(draft_record.id), test_tenant_id)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_di_wr_09_duplicate_month_year_raises(db, test_tenant_id, test_user, draft_record, senior):
    """DI-WR-09: 동일 연월 중복 생성 → 409."""
    with pytest.raises(HTTPException) as exc_info:
        await create_work_record(
            db, test_tenant_id, str(test_user.id),
            WorkRecordCreate(
                senior_id=senior.id,
                year=draft_record.year,
                month=draft_record.month,
                worked_hours=35.0,
                worked_days=17,
                amount_paid=351050,
            ),
            IP,
        )
    assert exc_info.value.status_code == 409
