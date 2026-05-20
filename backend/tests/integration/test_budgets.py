"""
DI-BG-01~06: Budget domain integration tests
— AnnualBudget CRUD, Expenditure 생성, 잔액 초과 경고.
"""
from __future__ import annotations
import uuid
from datetime import date

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.budget_expenditure import BudgetCategory
from app.models.business_unit import BusinessUnit, BusinessUnitType
from app.schemas.budget import AnnualBudgetCreate, AnnualBudgetUpdate, ExpenditureCreate
from app.services.budget_service import (
    create_budget,
    create_expenditure,
    delete_expenditure,
    get_budget,
    list_expenditures,
    update_budget,
)


IP = "127.0.0.1"


@pytest_asyncio.fixture
async def bu(db: AsyncSession, test_tenant_id: str):
    unit = BusinessUnit(
        tenant_id=uuid.UUID(test_tenant_id),
        name="예산 테스트 사업단",
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
async def budget(db, test_tenant_id, test_user, bu):
    return await create_budget(
        db, test_tenant_id, str(test_user.id),
        AnnualBudgetCreate(
            business_unit_id=bu.id,
            year=2026,
            total_wage_budget=10_000_000,
            manager_wage_budget=3_000_000,
            operation_budget=2_000_000,
            senior_count=10,
        ),
        IP,
    )


@pytest.mark.asyncio
async def test_di_bg_01_create_budget(db, test_tenant_id, test_user, bu):
    """DI-BG-01: 예산 생성 — DB에 저장되고 ID가 부여됨."""
    b = await create_budget(
        db, test_tenant_id, str(test_user.id),
        AnnualBudgetCreate(
            business_unit_id=bu.id,
            year=2025,
            total_wage_budget=8_000_000,
            manager_wage_budget=2_000_000,
            operation_budget=1_500_000,
            senior_count=8,
        ),
        IP,
    )
    assert b.id is not None
    assert b.year == 2025
    assert b.tenant_id == uuid.UUID(test_tenant_id)


@pytest.mark.asyncio
async def test_di_bg_02_get_budget(db, test_tenant_id, budget, bu):
    """DI-BG-02: (bu_id, year, tenant_id)로 예산 조회."""
    fetched = await get_budget(db, str(bu.id), budget.year, test_tenant_id)
    assert fetched.id == budget.id


@pytest.mark.asyncio
async def test_di_bg_03_get_budget_not_found(db, test_tenant_id):
    """DI-BG-03: 존재하지 않는 예산 조회 → 404."""
    with pytest.raises(HTTPException) as exc_info:
        await get_budget(db, str(uuid.uuid4()), 2026, test_tenant_id)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_di_bg_04_update_budget(db, test_tenant_id, test_user, budget):
    """DI-BG-04: 예산 수정 — senior_count 변경."""
    updated = await update_budget(
        db, str(budget.id), test_tenant_id, str(test_user.id),
        AnnualBudgetUpdate(senior_count=12),
        IP,
    )
    assert updated.senior_count == 12


@pytest.mark.asyncio
async def test_di_bg_05_expenditure_within_budget(db, test_tenant_id, test_user, budget):
    """DI-BG-05: 예산 내 지출 생성 → warnings 없음."""
    exp, warnings = await create_expenditure(
        db, test_tenant_id, str(test_user.id),
        ExpenditureCreate(
            annual_budget_id=budget.id,
            category=BudgetCategory.WAGE,
            item_name="3월 인건비",
            amount=500_000,
            expense_date=date(2026, 3, 31),
        ),
        IP,
    )
    assert exp.id is not None
    assert warnings == []


@pytest.mark.asyncio
async def test_di_bg_06_expenditure_over_budget_warning(db, test_tenant_id, test_user, budget):
    """DI-BG-06: 예산 초과 지출 → warning 포함."""
    exp, warnings = await create_expenditure(
        db, test_tenant_id, str(test_user.id),
        ExpenditureCreate(
            annual_budget_id=budget.id,
            category=BudgetCategory.WAGE,
            item_name="초과 인건비",
            amount=11_000_000,  # total_wage_budget(10M) 초과
            expense_date=date(2026, 4, 30),
        ),
        IP,
    )
    assert exp.id is not None
    assert len(warnings) == 1
    assert "초과" in warnings[0]


@pytest.mark.asyncio
async def test_di_bg_07_list_and_delete_expenditure(db, test_tenant_id, test_user, budget):
    """DI-BG-07: 지출 목록 조회, soft delete 후 목록에서 제거."""
    exp, _ = await create_expenditure(
        db, test_tenant_id, str(test_user.id),
        ExpenditureCreate(
            annual_budget_id=budget.id,
            category=BudgetCategory.OPERATION,
            item_name="사무용품",
            amount=50_000,
            expense_date=date(2026, 5, 10),
        ),
        IP,
    )

    items = await list_expenditures(db, str(budget.id), test_tenant_id)
    ids = [str(e.id) for e in items]
    assert str(exp.id) in ids

    await delete_expenditure(db, str(exp.id), test_tenant_id, str(test_user.id), IP)
    items_after = await list_expenditures(db, str(budget.id), test_tenant_id)
    ids_after = [str(e.id) for e in items_after]
    assert str(exp.id) not in ids_after
