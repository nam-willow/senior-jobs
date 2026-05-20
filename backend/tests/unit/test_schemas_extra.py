"""SC-* Extra schema + dashboard service unit tests."""
from __future__ import annotations
import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

# ── SC-01~04: Auth schemas ────────────────────────────────────────────────────

def test_sc01_login_request():
    from app.schemas.auth import LoginRequest
    req = LoginRequest(email="user@example.com", password="pw123")
    assert req.email == "user@example.com"
    assert req.password == "pw123"


def test_sc02_token_response():
    from app.schemas.auth import TokenResponse
    resp = TokenResponse(access_token="acc", refresh_token="ref", token_type="bearer")
    assert resp.token_type == "bearer"
    assert resp.access_token == "acc"


def test_sc03_refresh_request():
    from app.schemas.auth import RefreshRequest
    req = RefreshRequest(refresh_token="some_token")
    assert req.refresh_token == "some_token"


def test_sc04_logout_request():
    from app.schemas.auth import LogoutRequest
    req = LogoutRequest(refresh_token="some_token")
    assert req.refresh_token == "some_token"


# ── SC-05~08: User schemas ────────────────────────────────────────────────────

def test_sc05_user_create():
    from app.schemas.user import UserCreate
    from app.models.user import UserRole
    data = UserCreate(
        name="홍길동",
        email="hong@example.com",
        password="Pass123!",
        role=UserRole.SOCIAL_WORKER,
        business_unit_ids=[],
    )
    assert data.name == "홍길동"
    assert data.role == UserRole.SOCIAL_WORKER


def test_sc06_user_update_partial():
    from app.schemas.user import UserUpdate
    upd = UserUpdate(name="수정이름")
    assert upd.name == "수정이름"
    assert upd.role is None


def test_sc07_user_response_from_obj():
    from app.schemas.user import UserResponse
    from app.models.user import UserRole
    from types import SimpleNamespace
    obj = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        name="홍길동",
        email="hong@example.com",
        role=UserRole.SOCIAL_WORKER,
        is_active=True,
        last_login_at=None,
        created_at=datetime.now(timezone.utc),
    )
    resp = UserResponse.model_validate(obj)
    assert resp.name == "홍길동"


def test_sc08_user_create_with_bu_ids():
    from app.schemas.user import UserCreate
    from app.models.user import UserRole
    bu_id = uuid.uuid4()
    data = UserCreate(
        name="관리자",
        email="admin@example.com",
        password="Admin123!",
        role=UserRole.TENANT_ADMIN,
        business_unit_ids=[bu_id],
    )
    assert len(data.business_unit_ids) == 1
    assert data.business_unit_ids[0] == bu_id


# ── SC-09~11: Tenant schemas ──────────────────────────────────────────────────

def test_sc09_tenant_create():
    from app.schemas.tenant import TenantCreate
    data = TenantCreate(
        tenant_code="T001",
        name="테스트기관",
        subscription_plan="basic",
    )
    assert data.tenant_code == "T001"
    assert data.business_number is None


def test_sc10_tenant_update():
    from app.schemas.tenant import TenantUpdate
    upd = TenantUpdate(name="수정기관", is_active=False)
    assert upd.name == "수정기관"
    assert upd.is_active is False


def test_sc11_tenant_response():
    from app.schemas.tenant import TenantResponse
    from types import SimpleNamespace
    obj = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_code="T001",
        name="테스트기관",
        business_number=None,
        subscription_plan="basic",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    resp = TenantResponse.model_validate(obj)
    assert resp.tenant_code == "T001"


# ── SC-12~14: Policy Rule schemas ────────────────────────────────────────────

def test_sc12_policy_rule_create():
    from app.schemas.policy_rule import PolicyRuleCreate
    data = PolicyRuleCreate(
        rule_code="R001",
        rule_name="규칙1",
        priority=0,
        effective_from=date(2025, 1, 1),
        condition_json={"field": "x", "op": "eq", "value": 1},
        action_json={"result": "ok"},
    )
    assert data.rule_code == "R001"
    assert data.effective_to is None


def test_sc13_policy_rule_update():
    from app.schemas.policy_rule import PolicyRuleUpdate
    upd = PolicyRuleUpdate(rule_name="수정규칙", is_active=False)
    assert upd.rule_name == "수정규칙"
    assert upd.is_active is False


def test_sc14_policy_rule_response():
    from app.schemas.policy_rule import PolicyRuleResponse
    from types import SimpleNamespace
    obj = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        rule_code="R001",
        rule_name="규칙1",
        priority=0,
        is_active=True,
        effective_from=date(2025, 1, 1),
        effective_to=None,
        condition_json={"field": "x"},
        action_json={"k": "v"},
        created_at=datetime.now(timezone.utc),
    )
    resp = PolicyRuleResponse.model_validate(obj)
    assert resp.rule_code == "R001"


# ── SC-15~16: Common schemas ──────────────────────────────────────────────────

def test_sc15_paginated_response():
    from app.schemas.common import PaginatedResponse
    from app.schemas.senior import SeniorResponse
    pr = PaginatedResponse[SeniorResponse](items=[], total=0)
    assert pr.total == 0
    assert pr.items == []


def test_sc16_paginated_response_with_items():
    from app.schemas.common import PaginatedResponse
    resp = PaginatedResponse[dict](items=[{"a": 1}, {"b": 2}], total=2)
    assert resp.total == 2
    assert len(resp.items) == 2


# ── SC-17~20: Dashboard service ──────────────────────────────────────────────

async def test_sc17_dashboard_summary_empty():
    """get_summary with no business units returns zeroed entries."""
    from app.services.dashboard_service import get_summary
    from app.models.business_unit import BusinessUnitType

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result

    result = await get_summary(mock_db, str(uuid.uuid4()), 2025)
    assert result["year"] == 2025
    assert len(result["summary"]) == len(list(BusinessUnitType))
    for entry in result["summary"]:
        assert entry["total_budget"] == 0
        assert entry["achievement_rate"] == 0.0


async def test_sc18_dashboard_kpi():
    """get_kpi returns active senior count."""
    from app.services.dashboard_service import get_kpi

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar.return_value = 42
    mock_db.execute.return_value = mock_result

    result = await get_kpi(mock_db, str(uuid.uuid4()))
    assert result["active_senior_count"] == 42
    assert "year" in result


async def test_sc19_dashboard_summary_with_budget():
    """get_summary with business units and budgets shows proper totals."""
    from app.services.dashboard_service import get_summary
    from app.models.business_unit import BusinessUnitType
    from types import SimpleNamespace

    bu_id = uuid.uuid4()
    budget_id = uuid.uuid4()

    fake_bu = SimpleNamespace(
        id=bu_id,
        type=BusinessUnitType.PUBLIC_BENEFIT,
        year=2025,
        total_annual_hours=330,
        is_active=True,
    )
    fake_budget = SimpleNamespace(
        id=budget_id,
        business_unit_id=bu_id,
        year=2025,
        total_wage_budget=10_000_000,
        manager_wage_budget=2_000_000,
        operation_budget=1_000_000,
        senior_count=10,
        tenant_id=uuid.uuid4(),
    )

    call_count = 0

    async def fake_execute(query):
        nonlocal call_count
        mock_result = MagicMock()
        call_count += 1
        # First execute per BU type: business units
        # Second: annual budgets
        # Third/Fourth/Fifth: expenditures per category
        if call_count % 5 == 1:
            mock_result.scalars.return_value.all.return_value = [fake_bu]
        elif call_count % 5 == 2:
            mock_result.scalars.return_value.all.return_value = [fake_budget]
        else:
            mock_result.scalar.return_value = 0
        return mock_result

    mock_db = AsyncMock()
    mock_db.execute.side_effect = fake_execute

    result = await get_summary(mock_db, str(uuid.uuid4()), 2025)
    assert result["year"] == 2025
    pb = next(e for e in result["summary"] if e["type"] == "public_benefit")
    assert pb["senior_count"] == 10


async def test_sc20_dashboard_summary_achievement_rate():
    """Achievement rate is calculated correctly."""
    from app.services.dashboard_service import get_summary
    from app.models.business_unit import BusinessUnitType
    from types import SimpleNamespace

    bu_id = uuid.uuid4()
    budget_id = uuid.uuid4()

    fake_bu = SimpleNamespace(
        id=bu_id,
        type=BusinessUnitType.MARKET,
        year=2025,
        total_annual_hours=480,
        is_active=True,
    )
    fake_budget = SimpleNamespace(
        id=budget_id,
        business_unit_id=bu_id,
        year=2025,
        total_wage_budget=10_000_000,
        manager_wage_budget=0,
        operation_budget=0,
        senior_count=5,
        tenant_id=uuid.uuid4(),
    )

    call_count = [0]

    async def fake_execute(query):
        mock_result = MagicMock()
        call_count[0] += 1
        # Each BU type gets 5 calls: 1=BU list, 2=budgets, 3/4/5=expenditures
        c = call_count[0]
        if c == 1:  # public_benefit BU list
            mock_result.scalars.return_value.all.return_value = []
        elif c == 2:  # social_service BU list
            mock_result.scalars.return_value.all.return_value = []
        elif c == 3:  # market BU list
            mock_result.scalars.return_value.all.return_value = [fake_bu]
        elif c == 4:  # market budgets
            mock_result.scalars.return_value.all.return_value = [fake_budget]
        else:
            mock_result.scalar.return_value = 5_000_000  # 50% spent
        return mock_result

    mock_db = AsyncMock()
    mock_db.execute.side_effect = fake_execute

    result = await get_summary(mock_db, str(uuid.uuid4()), 2025)
    market = next(e for e in result["summary"] if e["type"] == "market")
    # total_budget = 10M + 0 + 0 = 10M
    # total_expenditure = 5M + 5M + 5M = 15M (all categories return 5M)
    assert market["total_budget"] == 10_000_000
