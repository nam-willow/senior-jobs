"""
WorkRecord 스키마 및 서비스 검증 (WR-01 ~ WR-10)
"""
import uuid

import pytest
from pydantic import ValidationError

from app.schemas.work_record import WorkRecordCreate, WorkRecordUpdate


# ── WR-01: 12월 입력 차단 ─────────────────────────────────────────────────────

def test_wr01_month_12_rejected():
    with pytest.raises(ValidationError, match="11월까지만 입력 가능"):
        WorkRecordCreate(
            senior_id=uuid.uuid4(), year=2026, month=12,
            worked_hours=30, worked_days=10, amount_paid=100000
        )


# ── WR-02: month=0 차단 ───────────────────────────────────────────────────────

def test_wr02_month_0_rejected():
    with pytest.raises(ValidationError, match="11월까지만 입력 가능"):
        WorkRecordCreate(
            senior_id=uuid.uuid4(), year=2026, month=0,
            worked_hours=30, worked_days=10, amount_paid=100000
        )


# ── WR-03: 정상 입력 (month=11) ───────────────────────────────────────────────

def test_wr03_valid_november():
    data = WorkRecordCreate(
        senior_id=uuid.uuid4(), year=2026, month=11,
        worked_hours=30, worked_days=10, amount_paid=100000
    )
    assert data.month == 11


# ── WR-04: 43h 초과 저장 불가 ────────────────────────────────────────────────

def test_wr04_hard_limit_43h():
    with pytest.raises(ValidationError, match="43"):
        WorkRecordCreate(
            senior_id=uuid.uuid4(), year=2026, month=7,
            worked_hours=43.1, worked_days=12, amount_paid=100000
        )


# ── WR-05: 42h 정상 저장 ─────────────────────────────────────────────────────

def test_wr05_exactly_42h_allowed():
    data = WorkRecordCreate(
        senior_id=uuid.uuid4(), year=2026, month=7,
        worked_hours=42.0, worked_days=14, amount_paid=168000
    )
    assert data.worked_hours == 42.0


# ── WR-06: 43h 저장 허용 (상한 경계) ─────────────────────────────────────────

def test_wr06_exactly_43h_allowed():
    data = WorkRecordCreate(
        senior_id=uuid.uuid4(), year=2026, month=7,
        worked_hours=43.0, worked_days=14, amount_paid=172000,
        overtime_reason="부득이한 사정"
    )
    assert data.worked_hours == 43.0


# ── WR-07: update 스키마 43h 초과 차단 ───────────────────────────────────────

def test_wr07_update_hard_limit():
    with pytest.raises(ValidationError, match="43"):
        WorkRecordUpdate(worked_hours=44.0)


# ── WR-08: update 스키마 None 허용 ───────────────────────────────────────────

def test_wr08_update_none_fields():
    data = WorkRecordUpdate()
    assert data.worked_hours is None
    assert data.worked_days is None


# ── WR-09: 완충 구간 (42 < h <= 43) 정의 검증 ────────────────────────────────

def test_wr09_soft_boundary():
    from app.schemas.work_record import MONTHLY_MAX_SOFT, MONTHLY_MAX_HARD
    assert MONTHLY_MAX_SOFT == 42.0
    assert MONTHLY_MAX_HARD == 43.0


# ── WR-10: 1월 정상 저장 ─────────────────────────────────────────────────────

def test_wr10_january_valid():
    data = WorkRecordCreate(
        senior_id=uuid.uuid4(), year=2026, month=1,
        worked_hours=30, worked_days=10, amount_paid=120000
    )
    assert data.month == 1
