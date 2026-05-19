"""
calculate_monthly_rows() 단위 테스트
TC-01 ~ TC-08 (공익활동형), SS-01 ~ SS-04 (사회서비스형), MK-01 ~ MK-03 (시장형)
"""
from unittest.mock import MagicMock

import pytest

from app.services.work_hours import calculate_monthly_rows


def _public(db, month, worked_so_far=None, session_hours=3):
    """공익활동형 공통 호출 헬퍼."""
    if worked_so_far is not None:
        db.query.return_value.filter.return_value.scalar.return_value = worked_so_far
    return calculate_monthly_rows(
        db=db,
        senior_id="senior-1",
        year=2025,
        month=month,
        business_unit_type="public_benefit",
        monthly_default_hours=30,
        monthly_max_hours=42,
        total_allocated_hours=330,
        session_hours=session_hours,
        carry_over_enabled=True,
    )


# ── 공익활동형 ─────────────────────────────────────────────────────────────────

def test_tc01_public_fixed_rows_before_july():
    """1~6월은 DB 조회 없이 고정 10행 반환."""
    mock_db = MagicMock()
    assert _public(mock_db, month=3) == 10
    mock_db.query.assert_not_called()


def test_tc02_public_july_on_track():
    """7월, 1~6월 180h 소화 → remaining=150h, ideal=10행, allowed_max=11 → 10행."""
    mock_db = MagicMock()
    assert _public(mock_db, month=7, worked_so_far=180) == 10


def test_tc03_public_july_with_deficit():
    """7월, 1~6월 150h 소화 → remaining=180h, ideal=12행, allowed_max=11 → 11행."""
    mock_db = MagicMock()
    assert _public(mock_db, month=7, worked_so_far=150) == 11


def test_tc04_public_august_adjustment():
    """8월, 1~7월 200h 소화 → remaining=130h, 4개월, ideal=11행, allowed_max=12 → 11행."""
    mock_db = MagicMock()
    assert _public(mock_db, month=8, worked_so_far=200) == 11


def test_tc05_public_november_near_end():
    """11월, 1~10월 290h 소화 → remaining=40h, 1개월, ideal=14행, allowed_max=14 → 14행."""
    mock_db = MagicMock()
    assert _public(mock_db, month=11, worked_so_far=290) == 14


def test_tc06_public_completed():
    """11월, 1~10월 330h(전체) 소화 → remaining=0 → 0행."""
    mock_db = MagicMock()
    assert _public(mock_db, month=11, worked_so_far=330) == 0


def test_tc07_public_short_session_hours():
    """
    session_hours=2, 7월, 180h 소화.
    ideal_rows = ceil(30/2) = 15,  allowed_max = min(10+1, 14) = 11 → 11행.
    MONTHLY_DEFAULT_ROWS/MAX_ROWS는 표준 3h 기준이므로 개인 세션 시간에 무관.
    """
    mock_db = MagicMock()
    assert _public(mock_db, month=7, worked_so_far=180, session_hours=2) == 11


def test_tc08_soft_delete_excluded():
    """
    DB가 반환하는 worked_so_far는 deleted_at IS NULL 기준 합계여야 한다.
    mock이 150h를 반환하면 (30h 삭제 기록 제외) 결과는 TC-03과 동일하게 11행.
    DB query가 실제로 호출되었는지도 확인한다.
    """
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.scalar.return_value = 150
    result = _public(mock_db, month=7)
    assert result == 11
    mock_db.query.assert_called_once()


# ── 사회서비스형 ────────────────────────────────────────────────────────────────

def _social(session_hours, month=5):
    return calculate_monthly_rows(
        db=MagicMock(),
        senior_id="senior-2",
        year=2025,
        month=month,
        business_unit_type="social_service",
        monthly_default_hours=60,
        monthly_max_hours=60,
        total_allocated_hours=660,
        session_hours=session_hours,
        carry_over_enabled=False,
    )


def test_ss01_social_service_fixed_rows():
    """사회서비스형, session=3h → ceil(60/3) = 20행."""
    assert _social(session_hours=3) == 20


def test_ss02_social_service_short_session():
    """사회서비스형, session=2h → ceil(60/2) = 30행."""
    assert _social(session_hours=2) == 30


def test_ss03_social_service_early_month():
    """사회서비스형, 3월(1~6월)도 고정 20행 — 이월 로직 없음."""
    assert _social(session_hours=3, month=3) == 20


def test_ss04_social_service_long_session():
    """사회서비스형, session=4h → ceil(60/4) = 15행."""
    assert _social(session_hours=4) == 15


# ── 시장형 ─────────────────────────────────────────────────────────────────────

def _market(monthly_default, session_hours, month=6):
    return calculate_monthly_rows(
        db=MagicMock(),
        senior_id="senior-3",
        year=2025,
        month=month,
        business_unit_type="market",
        monthly_default_hours=monthly_default,
        monthly_max_hours=monthly_default,
        total_allocated_hours=monthly_default * 11,
        session_hours=session_hours,
        carry_over_enabled=False,
    )


def test_mk01_market_admin_setting():
    """시장형, monthly=80h, session=4h → ceil(80/4) = 20행."""
    assert _market(monthly_default=80, session_hours=4) == 20


def test_mk02_market_max_session():
    """시장형, monthly=40h, session=8h → ceil(40/8) = 5행."""
    assert _market(monthly_default=40, session_hours=8) == 5


def test_mk03_market_month_independent():
    """시장형, 1월도 관리자 설정 고정 — 이월/조정 없음."""
    assert _market(monthly_default=80, session_hours=4, month=1) == 20


# ── month 범위 검증 ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("invalid_month", [0, 12, 13, -1])
def test_invalid_month_raises(invalid_month):
    """month 범위(1~11) 벗어나면 ValueError — 사회서비스/시장형도 포함."""
    with pytest.raises(ValueError, match="1~11"):
        calculate_monthly_rows(
            db=MagicMock(), senior_id="s", year=2025,
            month=invalid_month,
            business_unit_type="social_service",
            monthly_default_hours=60, monthly_max_hours=60,
            total_allocated_hours=660, session_hours=3,
            carry_over_enabled=False,
        )
