"""
서비스 레이어 단위 테스트 (mock DB)
SV-01 ~ SV-20
"""
import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.work_record import WorkRecordCreate, WorkRecordUpdate, MONTHLY_MAX_SOFT
from app.schemas.senior import SeniorCreate, SeniorUpdate
from app.schemas.budget import AnnualBudgetCreate, ExpenditureCreate
from app.schemas.consultation_log import ConsultationLogCreate
from app.models.monthly_work_records import WorkRecordStatus
from app.models.budget_expenditure import BudgetCategory


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────

def _make_async_db():
    db = AsyncMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    return db


def _make_senior(tid, buid, sid=None):
    s = MagicMock()
    s.id = sid or uuid.uuid4()
    s.tenant_id = tid
    s.business_unit_id = buid
    s.name = "테스트어르신"
    s.allocated_hours = 330
    s.default_session_hours = 3
    return s


def _make_bu(tid, buid=None):
    bu = MagicMock()
    bu.id = buid or uuid.uuid4()
    bu.tenant_id = tid
    bu.type = MagicMock()
    bu.type.value = "public_benefit"
    bu.monthly_default_hours = 30
    bu.monthly_max_hours = 42
    bu.total_annual_hours = 330
    bu.session_max_hours = 4
    bu.carry_over_enabled = True
    return bu


def _make_record(tid, sid, status=WorkRecordStatus.DRAFT, worked_hours=30.0):
    r = MagicMock()
    r.id = uuid.uuid4()
    r.tenant_id = tid
    r.senior_id = sid
    r.status = status
    r.worked_hours = worked_hours
    r.overtime_reason = None
    r.reject_reason = None
    r.soft_delete = MagicMock()
    return r


# ── SV-01: work_record DRAFT 상태 → SUBMITTED 상태전환 ───────────────────────

@pytest.mark.asyncio
async def test_sv01_submit_from_draft():
    from app.services.work_record_service import submit_work_record

    tid = uuid.uuid4()
    record = _make_record(tid, uuid.uuid4(), WorkRecordStatus.DRAFT)
    db = _make_async_db()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=record)))

    with patch("app.services.work_record_service.record_audit", new_callable=AsyncMock):
        result = await submit_work_record(db, str(record.id), str(tid), str(uuid.uuid4()), "127.0.0.1")

    assert result.status == WorkRecordStatus.SUBMITTED


# ── SV-02: 이미 SUBMITTED 상태에서 submit → 422 ────────────────────────────────

@pytest.mark.asyncio
async def test_sv02_submit_already_submitted():
    from fastapi import HTTPException
    from app.services.work_record_service import submit_work_record

    tid = uuid.uuid4()
    record = _make_record(tid, uuid.uuid4(), WorkRecordStatus.SUBMITTED)
    db = _make_async_db()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=record)))

    with pytest.raises(HTTPException) as exc:
        await submit_work_record(db, str(record.id), str(tid), str(uuid.uuid4()), "127.0.0.1")
    assert exc.value.status_code == 422


# ── SV-03: SUBMITTED → APPROVED ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sv03_approve_from_submitted():
    from app.services.work_record_service import approve_work_record

    tid = uuid.uuid4()
    record = _make_record(tid, uuid.uuid4(), WorkRecordStatus.SUBMITTED)
    db = _make_async_db()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=record)))

    with patch("app.services.work_record_service.record_audit", new_callable=AsyncMock):
        result = await approve_work_record(db, str(record.id), str(tid), str(uuid.uuid4()), "127.0.0.1")

    assert result.status == WorkRecordStatus.APPROVED
    assert result.approved_by is not None


# ── SV-04: DRAFT 상태에서 approve → 422 ──────────────────────────────────────

@pytest.mark.asyncio
async def test_sv04_approve_from_draft_rejected():
    from fastapi import HTTPException
    from app.services.work_record_service import approve_work_record

    tid = uuid.uuid4()
    record = _make_record(tid, uuid.uuid4(), WorkRecordStatus.DRAFT)
    db = _make_async_db()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=record)))

    with pytest.raises(HTTPException) as exc:
        await approve_work_record(db, str(record.id), str(tid), str(uuid.uuid4()), "127.0.0.1")
    assert exc.value.status_code == 422


# ── SV-05: SUBMITTED → REJECTED (사유 포함) ───────────────────────────────────

@pytest.mark.asyncio
async def test_sv05_reject_from_submitted():
    from app.services.work_record_service import reject_work_record

    tid = uuid.uuid4()
    record = _make_record(tid, uuid.uuid4(), WorkRecordStatus.SUBMITTED)
    db = _make_async_db()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=record)))

    with patch("app.services.work_record_service.record_audit", new_callable=AsyncMock):
        result = await reject_work_record(
            db, str(record.id), str(tid), str(uuid.uuid4()),
            reject_reason="시간 오류", ip_address="127.0.0.1"
        )

    assert result.status == WorkRecordStatus.REJECTED
    assert result.reject_reason == "시간 오류"


# ── SV-06: DRAFT 수정 허용 ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sv06_update_draft_allowed():
    from app.services.work_record_service import update_work_record

    tid = uuid.uuid4()
    record = _make_record(tid, uuid.uuid4(), WorkRecordStatus.DRAFT, worked_hours=30.0)
    db = _make_async_db()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=record)))

    data = WorkRecordUpdate(worked_hours=35.0, worked_days=12)
    with patch("app.services.work_record_service.record_audit", new_callable=AsyncMock):
        result, warnings = await update_work_record(
            db, str(record.id), str(tid), str(uuid.uuid4()), data, "127.0.0.1"
        )
    assert warnings == []


# ── SV-07: APPROVED 수정 차단 ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sv07_update_approved_rejected():
    from fastapi import HTTPException
    from app.services.work_record_service import update_work_record

    tid = uuid.uuid4()
    record = _make_record(tid, uuid.uuid4(), WorkRecordStatus.APPROVED)
    db = _make_async_db()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=record)))

    data = WorkRecordUpdate(worked_hours=35.0)
    with pytest.raises(HTTPException) as exc:
        await update_work_record(db, str(record.id), str(tid), str(uuid.uuid4()), data, "127.0.0.1")
    assert exc.value.status_code == 422


# ── SV-08: 42h 초과 시 overtime_reason 없으면 422 ───────────────────────────

@pytest.mark.asyncio
async def test_sv08_overtime_requires_reason():
    from fastapi import HTTPException
    from app.services.work_record_service import update_work_record

    tid = uuid.uuid4()
    record = _make_record(tid, uuid.uuid4(), WorkRecordStatus.DRAFT, worked_hours=30.0)
    db = _make_async_db()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=record)))

    data = WorkRecordUpdate(worked_hours=42.5)  # 42 < 42.5 <= 43
    with pytest.raises(HTTPException) as exc:
        await update_work_record(db, str(record.id), str(tid), str(uuid.uuid4()), data, "127.0.0.1")
    assert exc.value.status_code == 422


# ── SV-09: 42h 초과 + reason 있으면 경고만 ──────────────────────────────────

@pytest.mark.asyncio
async def test_sv09_overtime_with_reason_gives_warning():
    from app.services.work_record_service import update_work_record

    tid = uuid.uuid4()
    record = _make_record(tid, uuid.uuid4(), WorkRecordStatus.DRAFT, worked_hours=30.0)
    db = _make_async_db()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=record)))

    data = WorkRecordUpdate(worked_hours=42.5, overtime_reason="부득이한 사정")
    with patch("app.services.work_record_service.record_audit", new_callable=AsyncMock):
        result, warnings = await update_work_record(
            db, str(record.id), str(tid), str(uuid.uuid4()), data, "127.0.0.1"
        )
    assert any("초과" in w for w in warnings)


# ── SV-10: soft_delete 호출 확인 ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sv10_soft_delete_called():
    from app.services.work_record_service import soft_delete_work_record

    tid = uuid.uuid4()
    record = _make_record(tid, uuid.uuid4())
    db = _make_async_db()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=record)))

    with patch("app.services.work_record_service.record_audit", new_callable=AsyncMock):
        await soft_delete_work_record(db, str(record.id), str(tid), str(uuid.uuid4()), "127.0.0.1")

    record.soft_delete.assert_called_once()


# ── SV-11: BusinessUnit 공익형 기본값 적용 ───────────────────────────────────

@pytest.mark.asyncio
async def test_sv11_business_unit_public_benefit_defaults():
    from app.services.business_unit_service import create_business_unit
    from app.schemas.business_unit import BusinessUnitCreate, TYPE_DEFAULTS

    tid = str(uuid.uuid4())
    data = BusinessUnitCreate(name="공익", type="public_benefit", year=2026)
    db = _make_async_db()
    db.add = MagicMock()

    result_bu = MagicMock()
    result_bu.tenant_id = uuid.UUID(tid)
    db.refresh = AsyncMock()

    # flush가 id를 설정하는 것처럼 모킹
    created_bus = []
    original_add = db.add

    def capture_add(obj):
        created_bus.append(obj)
    db.add.side_effect = capture_add

    await create_business_unit(db, tid, str(uuid.uuid4()), data)
    assert len(created_bus) == 1
    bu = created_bus[0]
    assert bu.monthly_default_hours == TYPE_DEFAULTS["public_benefit"]["monthly_default_hours"]
    assert bu.session_max_hours == 4


# ── SV-12: BusinessUnit 시장형 필수 항목 없으면 ValidationError ─────────────

def test_sv12_market_missing_hours_validation():
    from pydantic import ValidationError
    from app.schemas.business_unit import BusinessUnitCreate

    with pytest.raises(ValidationError, match="시장형"):
        BusinessUnitCreate(name="시장", type="market", year=2026)


# ── SV-13: Senior 등록 — 사업단 없으면 404 ───────────────────────────────────

@pytest.mark.asyncio
async def test_sv13_create_senior_bu_not_found():
    from fastapi import HTTPException
    from app.services.senior_service import create_senior
    from app.schemas.senior import SeniorCreate

    tid = str(uuid.uuid4())
    data = SeniorCreate(
        business_unit_id=uuid.uuid4(), name="홍길동",
        birth_date=date(1950, 1, 1), hourly_wage=4000
    )
    db = _make_async_db()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

    with pytest.raises(HTTPException) as exc:
        await create_senior(db, tid, str(uuid.uuid4()), data, "127.0.0.1")
    assert exc.value.status_code == 404


# ── SV-14: Senior Soft Delete ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sv14_delete_senior_soft():
    from app.services.senior_service import delete_senior

    tid = uuid.uuid4()
    senior = MagicMock()
    senior.id = uuid.uuid4()
    senior.tenant_id = tid
    senior.name = "홍길동"
    senior.soft_delete = MagicMock()

    db = _make_async_db()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=senior)))

    with patch("app.services.senior_service.record_audit", new_callable=AsyncMock):
        await delete_senior(db, str(senior.id), str(tid), str(uuid.uuid4()), "127.0.0.1")

    senior.soft_delete.assert_called_once()


# ── SV-15: 월 42h 경고 구간 검증 ─────────────────────────────────────────────

def test_sv15_monthly_soft_limit():
    assert MONTHLY_MAX_SOFT == 42.0


# ── SV-16: ConsultationLog 어르신 없으면 404 ────────────────────────────────

@pytest.mark.asyncio
async def test_sv16_consultation_senior_not_found():
    from fastapi import HTTPException
    from app.services.consultation_log_service import create_consultation_log
    from datetime import datetime, timezone

    tid = str(uuid.uuid4())
    data = ConsultationLogCreate(
        senior_id=uuid.uuid4(),
        consultation_date=datetime.now(timezone.utc),
        method="phone",
        content="상담 내용",
        default_session_hours=3,
    )
    db = _make_async_db()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

    with pytest.raises(HTTPException) as exc:
        await create_consultation_log(db, tid, str(uuid.uuid4()), data, "127.0.0.1")
    assert exc.value.status_code == 404


# ── SV-17: RuleEngine 빈 컨텍스트 → 빈 dict ──────────────────────────────────

def test_sv17_rule_engine_empty_context():
    from app.services.rule_engine import RuleEngine
    engine = RuleEngine([])
    assert engine.evaluate({}) == {}


# ── SV-18: RuleEngine context 키 없는 경우 ───────────────────────────────────

def test_sv18_rule_engine_missing_field():
    from app.services.rule_engine import RuleEngine
    from unittest.mock import MagicMock
    from app.models.policy_rule import PolicyRule

    r = MagicMock(spec=PolicyRule)
    r.priority = 0
    r.condition_json = {"field": "nonexistent", "operator": "eq", "value": 1}
    r.action_json = {"hit": True}

    engine = RuleEngine([r])
    assert engine.evaluate({"other": 1}) == {}


# ── SV-19: budget_service 지출 초과 경고 ────────────────────────────────────

@pytest.mark.asyncio
async def test_sv19_expenditure_over_budget_warning():
    from app.services.budget_service import create_expenditure

    tid = str(uuid.uuid4())
    bid = uuid.uuid4()
    budget = MagicMock()
    budget.id = bid
    budget.tenant_id = uuid.UUID(tid)
    budget.total_wage_budget = 100000
    budget.manager_wage_budget = 50000
    budget.operation_budget = 30000

    data = ExpenditureCreate(
        annual_budget_id=bid,
        category=BudgetCategory.WAGE,
        item_name="임금",
        amount=200000,  # 예산 초과
        expense_date=date(2026, 3, 1),
    )

    exp_obj = MagicMock()
    exp_obj.id = uuid.uuid4()

    db = _make_async_db()
    db.add = MagicMock()

    # budget 조회 → budget 반환, 지출 합계 조회 → 200000 (초과)
    call_count = [0]
    def execute_side(*args, **kwargs):
        call_count[0] += 1
        mock_result = MagicMock()
        if call_count[0] == 1:
            mock_result.scalar_one_or_none = MagicMock(return_value=budget)
        else:
            mock_result.scalar = MagicMock(return_value=200000)
        return mock_result
    db.execute = AsyncMock(side_effect=execute_side)

    with patch("app.services.budget_service.record_audit", new_callable=AsyncMock):
        exp, warnings = await create_expenditure(db, tid, str(uuid.uuid4()), data, "127.0.0.1")

    assert any("초과" in w for w in warnings)


# ── SV-20: list_work_records 필터 조합 ────────────────────────────────────────

@pytest.mark.asyncio
async def test_sv20_list_work_records_no_filter():
    from app.services.work_record_service import list_work_records

    tid = str(uuid.uuid4())
    records = [_make_record(uuid.UUID(tid), uuid.uuid4()) for _ in range(3)]

    db = _make_async_db()
    db.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=records)))))

    result = await list_work_records(db, tid)
    assert len(result) == 3
