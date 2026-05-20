"""RT-* Router unit tests — happy-path coverage with mocked auth + DB."""
from __future__ import annotations
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.database import get_db, get_redis
from app.core.tenant import get_tenant_db
from app.core.permissions import get_current_user, CurrentUser
from app.models.user import UserRole
from app.models.monthly_work_records import WorkRecordStatus
from app.models.budget_expenditure import BudgetCategory
from app.models.consultation_log import ConsultationMethod

# ── Shared constants ──────────────────────────────────────────────────────────

TENANT_ID = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())
BU_ID = str(uuid.uuid4())


def _now():
    return datetime.now(timezone.utc)


FAKE_USER = CurrentUser(
    user_id=USER_ID,
    tenant_id=TENANT_ID,
    role="platform_admin",
    jti="test-jti",
)


# ── Mock DB factory ───────────────────────────────────────────────────────────

def make_mock_db(scalar_return=None, scalars_list=None):
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = scalars_list or []
    mock_result.scalar_one_or_none.return_value = scalar_return
    mock_result.scalar.return_value = 0
    mock_db.execute.return_value = mock_result
    mock_db.add = MagicMock()

    async def _refresh(obj):
        if getattr(obj, "created_at", None) is None and hasattr(obj, "created_at"):
            obj.created_at = _now()
        if getattr(obj, "id", None) is None and hasattr(obj, "id"):
            obj.id = uuid.uuid4()
        if getattr(obj, "tenant_id", None) is None and hasattr(obj, "tenant_id"):
            obj.tenant_id = uuid.UUID(TENANT_ID)
        # Apply SQLAlchemy column defaults that are NOT set at construction time
        if getattr(obj, "is_active", None) is None and hasattr(obj, "is_active"):
            obj.is_active = True

    mock_db.refresh.side_effect = _refresh
    return mock_db


# ── Client context manager ────────────────────────────────────────────────────

class _Client:
    def __init__(self, mock_db, mock_redis=None):
        self._mock_db = mock_db
        self._mock_redis = mock_redis or AsyncMock()

    async def __aenter__(self):
        async def _override_db() -> AsyncGenerator:
            yield self._mock_db

        app.dependency_overrides[get_current_user] = lambda: FAKE_USER
        app.dependency_overrides[get_db] = _override_db
        app.dependency_overrides[get_tenant_db] = _override_db
        app.dependency_overrides[get_redis] = lambda: self._mock_redis
        transport = ASGITransport(app=app)
        self._inner = AsyncClient(transport=transport, base_url="http://test")
        return await self._inner.__aenter__()

    async def __aexit__(self, *args):
        app.dependency_overrides.clear()
        return await self._inner.__aexit__(*args)


def client_ctx(mock_db=None, mock_redis=None):
    return _Client(mock_db or make_mock_db(), mock_redis)


# ── Fake response objects ─────────────────────────────────────────────────────

def fake_senior():
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.UUID(TENANT_ID),
        business_unit_id=uuid.UUID(BU_ID),
        name="홍길동",
        birth_date=date(1950, 1, 1),
        workplace="테스트직장",
        allocated_hours=330,
        hourly_wage=12000,
        default_session_hours=3,
        is_active=True,
        notes=None,
        created_by=uuid.UUID(USER_ID),
        created_at=_now(),
        deleted_at=None,
    )


def fake_work_record():
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.UUID(TENANT_ID),
        senior_id=uuid.uuid4(),
        year=2025,
        month=1,
        worked_hours=Decimal("30.0"),
        worked_days=10,
        amount_paid=360000,
        status=WorkRecordStatus.DRAFT,
        approved_by=None,
        approved_at=None,
        reject_reason=None,
        overtime_reason=None,
        created_by=uuid.UUID(USER_ID),
        created_at=_now(),
        deleted_at=None,
    )


def fake_budget():
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.UUID(TENANT_ID),
        business_unit_id=uuid.UUID(BU_ID),
        year=2025,
        total_wage_budget=10_000_000,
        manager_wage_budget=2_000_000,
        operation_budget=1_000_000,
        senior_count=10,
        created_by=uuid.UUID(USER_ID),
        created_at=_now(),
        updated_at=None,
    )


def fake_expenditure():
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.UUID(TENANT_ID),
        annual_budget_id=uuid.uuid4(),
        category=BudgetCategory.WAGE,
        item_name="테스트항목",
        amount=100_000,
        expense_date=date(2025, 1, 15),
        note=None,
        created_by=uuid.UUID(USER_ID),
        created_at=_now(),
        deleted_at=None,
    )


def fake_consultation_log():
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.UUID(TENANT_ID),
        senior_id=uuid.uuid4(),
        social_worker_id=uuid.UUID(USER_ID),
        consultation_date=_now(),
        method=ConsultationMethod.PHONE,
        content="상담 내용",
        memo=None,
        default_session_hours=3,
        created_at=_now(),
        deleted_at=None,
    )


def fake_bu():
    return SimpleNamespace(
        id=uuid.UUID(BU_ID),
        tenant_id=uuid.UUID(TENANT_ID),
        type="public_benefit",
        year=2025,
        name="테스트사업단",
        monthly_default_hours=30,
        monthly_max_hours=42,
        total_annual_hours=330,
        session_default_hours=3,
        session_max_hours=4,
        carry_over_enabled=True,
        description=None,
        is_active=True,
        created_at=_now(),
        updated_at=None,
    )


def fake_policy_rule():
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.UUID(TENANT_ID),
        rule_code="R001",
        rule_name="규칙1",
        priority=0,
        is_active=True,
        effective_from=date(2025, 1, 1),
        effective_to=None,
        condition_json={"field": "x", "op": "eq", "value": 1},
        action_json={"key": "val"},
        created_at=_now(),
    )


def fake_tenant():
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_code="T001",
        name="테스트기관",
        business_number="123-45-67890",
        subscription_plan="basic",
        is_active=True,
        created_at=_now(),
    )


def fake_user_obj():
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.UUID(TENANT_ID),
        name="테스트유저",
        email="test@example.com",
        role=UserRole.SOCIAL_WORKER,
        is_active=True,
        last_login_at=None,
        created_at=_now(),
        password_hash="hashed",
    )


def fake_audit_log():
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.UUID(TENANT_ID),
        user_id=uuid.UUID(USER_ID),
        action_type="CREATE",
        target_table="seniors",
        target_id=uuid.uuid4(),
        ip_address="127.0.0.1",
        created_at=_now(),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# RT-01~05: Seniors router
# ═══════════════════════════════════════════════════════════════════════════════

async def test_rt01_list_seniors():
    with patch("app.services.senior_service.list_seniors", return_value=[]):
        async with client_ctx() as c:
            resp = await c.get("/api/v1/seniors/")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


async def test_rt02_create_senior():
    s = fake_senior()
    with patch("app.services.senior_service.create_senior", return_value=s):
        async with client_ctx() as c:
            resp = await c.post("/api/v1/seniors/", json={
                "business_unit_id": BU_ID,
                "name": "홍길동",
                "birth_date": "1950-01-01",
                "hourly_wage": 12000,
                "default_session_hours": 3,
            })
    assert resp.status_code == 201


async def test_rt03_get_senior():
    s = fake_senior()
    with patch("app.services.senior_service.get_senior", return_value=s):
        async with client_ctx() as c:
            resp = await c.get(f"/api/v1/seniors/{s.id}")
    assert resp.status_code == 200


async def test_rt04_update_senior():
    s = fake_senior()
    with patch("app.services.senior_service.update_senior", return_value=s):
        async with client_ctx() as c:
            resp = await c.put(f"/api/v1/seniors/{s.id}", json={"name": "수정이름"})
    assert resp.status_code == 200


async def test_rt05_delete_senior():
    with patch("app.services.senior_service.delete_senior", return_value=None):
        async with client_ctx() as c:
            resp = await c.delete(f"/api/v1/seniors/{uuid.uuid4()}")
    assert resp.status_code == 204


# ═══════════════════════════════════════════════════════════════════════════════
# RT-06~09: Business Units router
# ═══════════════════════════════════════════════════════════════════════════════

async def test_rt06_list_business_units():
    with patch("app.services.business_unit_service.list_business_units", return_value=[]):
        async with client_ctx() as c:
            resp = await c.get("/api/v1/business-units/")
    assert resp.status_code == 200


async def test_rt07_create_business_unit():
    bu = fake_bu()
    with patch("app.services.business_unit_service.create_business_unit", return_value=bu):
        async with client_ctx() as c:
            resp = await c.post("/api/v1/business-units/", json={
                "type": "market",
                "year": 2025,
                "name": "시장형",
                "monthly_default_hours": 40,
                "monthly_max_hours": 43,
                "total_annual_hours": 480,
                "session_default_hours": 4,
                "session_max_hours": 8,
                "carry_over_enabled": False,
            })
    assert resp.status_code == 201


async def test_rt08_update_business_unit():
    bu = fake_bu()
    with patch("app.services.business_unit_service.update_business_unit", return_value=bu):
        async with client_ctx() as c:
            resp = await c.put(f"/api/v1/business-units/{BU_ID}", json={"name": "수정됨"})
    assert resp.status_code == 200


async def test_rt09_delete_business_unit():
    with patch("app.services.business_unit_service.delete_business_unit", return_value=None):
        async with client_ctx() as c:
            resp = await c.delete(f"/api/v1/business-units/{BU_ID}")
    assert resp.status_code == 204


# ═══════════════════════════════════════════════════════════════════════════════
# RT-10~17: Work Records router
# ═══════════════════════════════════════════════════════════════════════════════

async def test_rt10_list_work_records():
    with patch("app.services.work_record_service.list_work_records", return_value=[]):
        async with client_ctx() as c:
            resp = await c.get("/api/v1/work-records/")
    assert resp.status_code == 200


async def test_rt11_create_work_record():
    rec = fake_work_record()
    with patch("app.services.work_record_service.create_work_record", return_value=(rec, [])):
        async with client_ctx() as c:
            resp = await c.post("/api/v1/work-records/", json={
                "senior_id": str(rec.senior_id),
                "year": 2025,
                "month": 1,
                "worked_hours": "30.0",
                "worked_days": 10,
                "amount_paid": 360000,
            })
    assert resp.status_code == 201


async def test_rt12_update_work_record():
    rec = fake_work_record()
    with patch("app.services.work_record_service.update_work_record", return_value=(rec, [])):
        async with client_ctx() as c:
            resp = await c.put(f"/api/v1/work-records/{rec.id}", json={"worked_hours": "32.0"})
    assert resp.status_code == 200


async def test_rt13_delete_work_record():
    with patch("app.services.work_record_service.soft_delete_work_record", return_value=None):
        async with client_ctx() as c:
            resp = await c.delete(f"/api/v1/work-records/{uuid.uuid4()}")
    assert resp.status_code == 204


async def test_rt14_submit_work_record():
    rec = fake_work_record()
    rec.status = WorkRecordStatus.SUBMITTED
    with patch("app.services.work_record_service.submit_work_record", return_value=rec):
        async with client_ctx() as c:
            resp = await c.post(f"/api/v1/work-records/{rec.id}/submit")
    assert resp.status_code == 200


async def test_rt15_approve_work_record():
    rec = fake_work_record()
    rec.status = WorkRecordStatus.APPROVED
    with patch("app.services.work_record_service.approve_work_record", return_value=rec):
        async with client_ctx() as c:
            resp = await c.post(f"/api/v1/work-records/{rec.id}/approve")
    assert resp.status_code == 200


async def test_rt16_reject_work_record():
    rec = fake_work_record()
    rec.status = WorkRecordStatus.REJECTED
    rec.reject_reason = "사유"
    with patch("app.services.work_record_service.reject_work_record", return_value=rec):
        async with client_ctx() as c:
            resp = await c.post(f"/api/v1/work-records/{rec.id}/reject", json={"reject_reason": "사유"})
    assert resp.status_code == 200


async def test_rt17_work_record_with_warning():
    """Create work record returns warnings."""
    rec = fake_work_record()
    rec.worked_hours = Decimal("42.5")
    rec.overtime_reason = "초과사유"
    with patch("app.services.work_record_service.create_work_record", return_value=(rec, ["overtime_warning"])):
        async with client_ctx() as c:
            resp = await c.post("/api/v1/work-records/", json={
                "senior_id": str(rec.senior_id),
                "year": 2025,
                "month": 2,
                "worked_hours": "42.5",
                "worked_days": 14,
                "amount_paid": 510000,
                "overtime_reason": "초과사유",
            })
    assert resp.status_code == 201
    assert resp.json()["warnings"] == ["overtime_warning"]


# ═══════════════════════════════════════════════════════════════════════════════
# RT-18~23: Budgets router
# ═══════════════════════════════════════════════════════════════════════════════

async def test_rt18_get_budget():
    b = fake_budget()
    with patch("app.services.budget_service.get_budget", return_value=b):
        async with client_ctx() as c:
            resp = await c.get(f"/api/v1/budgets/{BU_ID}/2025")
    assert resp.status_code == 200


async def test_rt19_create_budget():
    b = fake_budget()
    with patch("app.services.budget_service.create_budget", return_value=b):
        async with client_ctx() as c:
            resp = await c.post("/api/v1/budgets/", json={
                "business_unit_id": BU_ID,
                "year": 2025,
                "total_wage_budget": 10_000_000,
                "manager_wage_budget": 2_000_000,
                "operation_budget": 1_000_000,
                "senior_count": 10,
            })
    assert resp.status_code == 201


async def test_rt20_update_budget():
    b = fake_budget()
    with patch("app.services.budget_service.update_budget", return_value=b):
        async with client_ctx() as c:
            resp = await c.put(f"/api/v1/budgets/{b.id}", json={"senior_count": 12})
    assert resp.status_code == 200


async def test_rt21_list_expenditures():
    with patch("app.services.budget_service.list_expenditures", return_value=[]):
        async with client_ctx() as c:
            resp = await c.get(f"/api/v1/budgets/expenditures/{uuid.uuid4()}")
    assert resp.status_code == 200


async def test_rt22_create_expenditure():
    exp = fake_expenditure()
    with patch("app.services.budget_service.create_expenditure", return_value=(exp, [])):
        async with client_ctx() as c:
            resp = await c.post("/api/v1/budgets/expenditures/", json={
                "annual_budget_id": str(exp.annual_budget_id),
                "category": "wage",
                "item_name": "테스트항목",
                "amount": 100_000,
                "expense_date": "2025-01-15",
            })
    assert resp.status_code == 201


async def test_rt23_delete_expenditure():
    with patch("app.services.budget_service.delete_expenditure", return_value=None):
        async with client_ctx() as c:
            resp = await c.delete(f"/api/v1/budgets/expenditures/{uuid.uuid4()}")
    assert resp.status_code == 204


# ═══════════════════════════════════════════════════════════════════════════════
# RT-24~27: Consultation Logs router
# ═══════════════════════════════════════════════════════════════════════════════

async def test_rt24_list_consultation_logs():
    with patch("app.services.consultation_log_service.list_consultation_logs", return_value=[]):
        async with client_ctx() as c:
            resp = await c.get("/api/v1/consultation-logs/")
    assert resp.status_code == 200


async def test_rt25_create_consultation_log():
    log = fake_consultation_log()
    with patch("app.services.consultation_log_service.create_consultation_log", return_value=log):
        async with client_ctx() as c:
            resp = await c.post("/api/v1/consultation-logs/", json={
                "senior_id": str(log.senior_id),
                "consultation_date": _now().isoformat(),
                "method": "phone",
                "content": "상담 내용",
                "default_session_hours": 3,
            })
    assert resp.status_code == 201


async def test_rt26_update_consultation_log():
    log = fake_consultation_log()
    with patch("app.services.consultation_log_service.update_consultation_log", return_value=log):
        async with client_ctx() as c:
            resp = await c.put(f"/api/v1/consultation-logs/{log.id}", json={"content": "수정내용"})
    assert resp.status_code == 200


async def test_rt27_delete_consultation_log():
    with patch("app.services.consultation_log_service.delete_consultation_log", return_value=None):
        async with client_ctx() as c:
            resp = await c.delete(f"/api/v1/consultation-logs/{uuid.uuid4()}")
    assert resp.status_code == 204


# ═══════════════════════════════════════════════════════════════════════════════
# RT-28~29: Dashboard router
# ═══════════════════════════════════════════════════════════════════════════════

async def test_rt28_dashboard_summary():
    fake_summary = {"year": 2025, "summary": []}
    with patch("app.services.dashboard_service.get_summary", return_value=fake_summary):
        async with client_ctx() as c:
            resp = await c.get("/api/v1/dashboard/summary")
    assert resp.status_code == 200
    assert resp.json()["year"] == 2025


async def test_rt29_dashboard_kpi():
    fake_kpi = {"year": 2025, "active_senior_count": 42}
    with patch("app.services.dashboard_service.get_kpi", return_value=fake_kpi):
        async with client_ctx() as c:
            resp = await c.get("/api/v1/dashboard/kpi")
    assert resp.status_code == 200
    assert resp.json()["active_senior_count"] == 42


# ═══════════════════════════════════════════════════════════════════════════════
# RT-30~33: Auth router
# ═══════════════════════════════════════════════════════════════════════════════

async def test_rt30_login():
    token_resp = {"access_token": "acc", "refresh_token": "ref", "token_type": "bearer"}
    with patch("app.services.auth_service.login", return_value=token_resp):
        async with client_ctx() as c:
            resp = await c.post("/api/v1/auth/login", json={
                "email": "admin@example.com",
                "password": "Admin1234!",
            })
    assert resp.status_code == 200
    assert resp.json()["token_type"] == "bearer"


async def test_rt31_refresh():
    token_resp = {"access_token": "new_acc", "refresh_token": "new_ref", "token_type": "bearer"}
    with patch("app.services.auth_service.refresh", return_value=token_resp):
        async with client_ctx() as c:
            resp = await c.post("/api/v1/auth/refresh", json={"refresh_token": "old_ref"})
    assert resp.status_code == 200


async def test_rt32_logout():
    with patch("app.services.auth_service.logout", return_value=None):
        async with client_ctx() as c:
            resp = await c.post("/api/v1/auth/logout", json={"refresh_token": "some_token"})
    assert resp.status_code == 204


# ═══════════════════════════════════════════════════════════════════════════════
# RT-33~37: Tenants router (DB-direct)
# ═══════════════════════════════════════════════════════════════════════════════

async def test_rt33_list_tenants():
    t = fake_tenant()
    db = make_mock_db(scalars_list=[t])
    async with client_ctx(db) as c:
        resp = await c.get("/api/v1/tenants/")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


async def test_rt34_create_tenant():
    db = make_mock_db()
    # Extra refresh side effect: also populate is_active for Tenant
    _orig = db.refresh.side_effect

    async def _refresh_extra(obj):
        await _orig(obj)
        if hasattr(obj, "is_active") and obj.is_active is None:
            obj.is_active = True

    db.refresh.side_effect = _refresh_extra
    async with client_ctx(db) as c:
        resp = await c.post("/api/v1/tenants/", json={
            "tenant_code": "T001",
            "name": "테스트기관",
            "subscription_plan": "basic",
        })
    assert resp.status_code == 201


async def test_rt35_update_tenant_found():
    t = fake_tenant()
    db = make_mock_db(scalar_return=t)
    async with client_ctx(db) as c:
        resp = await c.put(f"/api/v1/tenants/{t.id}", json={"name": "수정기관"})
    assert resp.status_code == 200


async def test_rt36_update_tenant_not_found():
    db = make_mock_db(scalar_return=None)
    async with client_ctx(db) as c:
        resp = await c.put(f"/api/v1/tenants/{uuid.uuid4()}", json={"name": "수정기관"})
    assert resp.status_code == 404


async def test_rt37_delete_tenant_found():
    t = fake_tenant()
    db = make_mock_db(scalar_return=t)
    async with client_ctx(db) as c:
        resp = await c.delete(f"/api/v1/tenants/{t.id}")
    assert resp.status_code == 204


async def test_rt38_delete_tenant_not_found():
    db = make_mock_db(scalar_return=None)
    async with client_ctx(db) as c:
        resp = await c.delete(f"/api/v1/tenants/{uuid.uuid4()}")
    assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# RT-39~43: Users router (DB-direct)
# ═══════════════════════════════════════════════════════════════════════════════

async def test_rt39_list_users():
    u = fake_user_obj()
    db = make_mock_db(scalars_list=[u])
    async with client_ctx(db) as c:
        resp = await c.get("/api/v1/users/")
    assert resp.status_code == 200


async def test_rt40_create_user():
    # record_audit is imported directly in users.py — patch at the router level
    with patch("app.routers.users.hash_password", return_value="hashed_pw"):
        with patch("app.routers.users.record_audit", new=AsyncMock(return_value=None)):
            async with client_ctx() as c:
                resp = await c.post("/api/v1/users/", json={
                    "name": "새유저",
                    "email": "newuser@example.com",
                    "password": "Password1!",
                    "role": "social_worker",
                    "business_unit_ids": [],
                })
    assert resp.status_code == 201


async def test_rt41_get_user_found():
    u = fake_user_obj()
    db = make_mock_db(scalar_return=u)
    async with client_ctx(db) as c:
        resp = await c.get(f"/api/v1/users/{u.id}")
    assert resp.status_code == 200


async def test_rt42_get_user_not_found():
    db = make_mock_db(scalar_return=None)
    async with client_ctx(db) as c:
        resp = await c.get(f"/api/v1/users/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_rt43_delete_user_found():
    u = fake_user_obj()
    db = make_mock_db(scalar_return=u)
    with patch("app.services.audit.record_audit", return_value=None):
        async with client_ctx(db) as c:
            resp = await c.delete(f"/api/v1/users/{u.id}")
    assert resp.status_code == 204


# ═══════════════════════════════════════════════════════════════════════════════
# RT-44~46: Audit Logs router (DB-direct)
# ═══════════════════════════════════════════════════════════════════════════════

async def test_rt44_list_audit_logs_empty():
    db = make_mock_db(scalars_list=[])
    async with client_ctx(db) as c:
        resp = await c.get("/api/v1/audit-logs/")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


async def test_rt45_list_audit_logs_with_filters():
    al = fake_audit_log()
    db = make_mock_db(scalars_list=[al])
    from urllib.parse import urlencode
    params = urlencode({
        "target_table": "seniors",
        "user_id": USER_ID,
    })
    async with client_ctx(db) as c:
        resp = await c.get(f"/api/v1/audit-logs/?{params}")
    assert resp.status_code == 200


async def test_rt46_list_audit_logs_date_filter():
    db = make_mock_db(scalars_list=[])
    async with client_ctx(db) as c:
        resp = await c.get("/api/v1/audit-logs/?from_dt=2025-01-01T00:00:00&to_dt=2025-12-31T23:59:59")
    assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# RT-47~51: Policy Rules router (DB-direct)
# ═══════════════════════════════════════════════════════════════════════════════

async def test_rt47_list_policy_rules():
    pr = fake_policy_rule()
    db = make_mock_db(scalars_list=[pr])
    async with client_ctx(db) as c:
        resp = await c.get("/api/v1/policy-rules/")
    assert resp.status_code == 200


async def test_rt48_create_policy_rule():
    # record_audit is imported directly in policy_rules.py — patch at router level
    with patch("app.routers.policy_rules.record_audit", new=AsyncMock(return_value=None)):
        async with client_ctx() as c:
            resp = await c.post("/api/v1/policy-rules/", json={
                "rule_code": "R001",
                "rule_name": "규칙1",
                "priority": 0,
                "effective_from": "2025-01-01",
                "condition_json": {"field": "x", "op": "eq", "value": 1},
                "action_json": {"key": "val"},
            })
    assert resp.status_code == 201


async def test_rt49_update_policy_rule_found():
    pr = fake_policy_rule()
    db = make_mock_db(scalar_return=pr)
    with patch("app.services.audit.record_audit", return_value=None):
        async with client_ctx(db) as c:
            resp = await c.put(f"/api/v1/policy-rules/{pr.id}", json={"rule_name": "수정규칙"})
    assert resp.status_code == 200


async def test_rt50_update_policy_rule_not_found():
    db = make_mock_db(scalar_return=None)
    async with client_ctx(db) as c:
        resp = await c.put(f"/api/v1/policy-rules/{uuid.uuid4()}", json={"rule_name": "없음"})
    assert resp.status_code == 404


async def test_rt51_delete_policy_rule_found():
    pr = fake_policy_rule()
    db = make_mock_db(scalar_return=pr)
    with patch("app.services.audit.record_audit", return_value=None):
        async with client_ctx(db) as c:
            resp = await c.delete(f"/api/v1/policy-rules/{pr.id}")
    assert resp.status_code == 204


async def test_rt52_delete_policy_rule_not_found():
    db = make_mock_db(scalar_return=None)
    async with client_ctx(db) as c:
        resp = await c.delete(f"/api/v1/policy-rules/{uuid.uuid4()}")
    assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# RT-53: Health check
# ═══════════════════════════════════════════════════════════════════════════════

async def test_rt53_health_check():
    async with client_ctx() as c:
        resp = await c.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
