"""
validate_work_feasibility() 단위 테스트
F-01 ~ F-10

구현 상의 주요 결정:
- max_achievable = session_hours * working_days  (MONTHLY_MAX_HOURS 캡 미적용)
  → 사회서비스형(목표 60h)이 feasible=True 처리되어야 하므로
- unavoidable_deficit 조건: absolute_max <= target_hours  (명세 코드 < 대신 <=)
  → F-10: absolute_max=40 == target=40 일 때도 deficit으로 간주
"""
import pytest

from app.services.work_hours import validate_work_feasibility


# ── F-01: 공익활동형, 정상 달성 ────────────────────────────────────────────────
def test_f01_public_feasible():
    result = validate_work_feasibility(3, 10, 30, session_max=4)
    assert result["feasible"] is True
    assert result["violations"] == []
    assert result["suggestions"] == []
    assert result["max_achievable"] == 30


# ── F-02: 공익활동형, 일수 부족 ────────────────────────────────────────────────
def test_f02_public_insufficient_days():
    result = validate_work_feasibility(3, 8, 30, session_max=4)
    assert result["feasible"] is False
    types = [s["type"] for s in result["suggestions"]]
    assert "increase_days" in types
    assert "increase_session_hours" in types
    assert "unavoidable_deficit" not in types
    # increase_session_hours: ceil(30/8)=4h ≤ session_max=4
    sh_sug = next(s for s in result["suggestions"] if s["type"] == "increase_session_hours")
    assert "4h" in sh_sug["desc"]


# ── F-03: 공익활동형, 어떤 조합으로도 불가 ─────────────────────────────────────
def test_f03_public_unavoidable_deficit():
    result = validate_work_feasibility(3, 2, 30, session_max=4)
    assert result["feasible"] is False
    types = [s["type"] for s in result["suggestions"]]
    assert "unavoidable_deficit" in types
    # increase_session_hours: ceil(30/2)=15h > 4 → 없음
    assert "increase_session_hours" not in types
    deficit = next(s for s in result["suggestions"] if s["type"] == "unavoidable_deficit")
    assert deficit["max_achievable"] == 8  # 4h × 2일


# ── F-04: 공익활동형, 세션 시간 초과 ────────────────────────────────────────────
def test_f04_session_hours_violation():
    result = validate_work_feasibility(5, 10, 30, session_max=4)
    assert len(result["violations"]) == 1
    assert "4h 초과" in result["violations"][0]
    # 상한(4h) 적용 후 max=40 ≥ 30 → feasible
    assert result["feasible"] is True


# ── F-05: 사회서비스형, 정상 달성 ──────────────────────────────────────────────
def test_f05_social_service_feasible():
    result = validate_work_feasibility(3, 20, 60, session_max=8)
    assert result["feasible"] is True
    assert result["violations"] == []
    assert result["max_achievable"] == 60  # MONTHLY_MAX_HOURS 캡 미적용


# ── F-06: 사회서비스형, 세션 시간 초과 ──────────────────────────────────────────
def test_f06_social_service_session_violation():
    result = validate_work_feasibility(10, 10, 60, session_max=8)
    assert len(result["violations"]) == 1
    assert "8h 초과" in result["violations"][0]
    # 8h 적용 후 max=80 ≥ 60 → feasible
    assert result["feasible"] is True


# ── F-07: 사회서비스형, 시간 또는 일수 조정 필요 ────────────────────────────────
def test_f07_social_service_needs_adjustment():
    result = validate_work_feasibility(4, 10, 60, session_max=8)
    assert result["feasible"] is False
    types = [s["type"] for s in result["suggestions"]]
    assert "increase_days" in types
    assert "increase_session_hours" in types
    assert "unavoidable_deficit" not in types  # absolute_max=80 > 60
    # increase_days: ceil(60/4)=15일
    day_sug = next(s for s in result["suggestions"] if s["type"] == "increase_days")
    assert "15일" in day_sug["desc"]
    # increase_session_hours: ceil(60/10)=6h
    sh_sug = next(s for s in result["suggestions"] if s["type"] == "increase_session_hours")
    assert "6h" in sh_sug["desc"]


# ── F-08: 시장형, 정상 달성 ────────────────────────────────────────────────────
def test_f08_market_feasible():
    result = validate_work_feasibility(8, 10, 80, session_max=8)
    assert result["feasible"] is True
    assert result["violations"] == []
    assert result["max_achievable"] == 80


# ── F-09: 시장형, 세션 시간 초과 ────────────────────────────────────────────────
def test_f09_market_session_violation():
    result = validate_work_feasibility(9, 10, 80, session_max=8)
    assert len(result["violations"]) == 1
    assert "8h 초과" in result["violations"][0]
    assert result["feasible"] is True


# ── F-10: 시장형, 최대 도달 시 unavoidable_deficit ────────────────────────────
def test_f10_market_unavoidable_deficit():
    """
    session=4h, 5일, 목표=40h, session_max=8h.
    max_achievable=20 < 40 → not feasible.
    absolute_max = 8×5 = 40 ≤ target=40 → unavoidable_deficit.
    """
    result = validate_work_feasibility(4, 5, 40, session_max=8)
    assert result["feasible"] is False
    types = [s["type"] for s in result["suggestions"]]
    assert "unavoidable_deficit" in types
    deficit = next(s for s in result["suggestions"] if s["type"] == "unavoidable_deficit")
    assert deficit["max_achievable"] == 40
