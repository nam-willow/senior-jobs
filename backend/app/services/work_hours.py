from __future__ import annotations
import math
from sqlalchemy import func
from sqlalchemy.orm import Session


# ── 공익활동형 행 수 계산 기준 ─────────────────────────────────────────────────
# 점진적 상한(allowed_max)은 표준 세션 3h 기준 고정값으로 계산한다.
# 이렇게 해야 세션 시간이 달라도(TC-07) 상한 증가폭이 일관된다.
_PUBLIC_STANDARD_SESSION = 3


def calculate_monthly_rows(
    db: Session,
    senior_id: str,
    year: int,
    month: int,
    business_unit_type: str,      # "public_benefit" | "social_service" | "market"
    monthly_default_hours: int,
    monthly_max_hours: int,
    total_allocated_hours: int,
    session_hours: int,
    carry_over_enabled: bool,
) -> int:
    if not (1 <= month <= 11):
        raise ValueError(f"월은 1~11만 허용됩니다. 입력값: {month}")

    # ── 사회서비스형: 매월 고정 (이월 없음) ──────────────────────────────────
    if business_unit_type == "social_service":
        return math.ceil(monthly_default_hours / session_hours)

    # ── 시장형: 매월 고정 (관리자 설정 기준, 이월 없음) ─────────────────────
    if business_unit_type == "market":
        return math.ceil(monthly_default_hours / session_hours)

    # ── 공익활동형: 이월 포함 점진적 조정 ────────────────────────────────────
    ADJUSTMENT_START_MONTH = 7

    # 점진적 상한은 표준 세션(3h) 기준 고정 — 개인 세션 시간 무관
    MONTHLY_DEFAULT_ROWS = math.ceil(monthly_default_hours / _PUBLIC_STANDARD_SESSION)
    MONTHLY_MAX_ROWS = math.ceil(monthly_max_hours / _PUBLIC_STANDARD_SESSION)

    # 1~6월: 고정 행 수 (어르신 심리 안정)
    if month < ADJUSTMENT_START_MONTH:
        return MONTHLY_DEFAULT_ROWS

    # 7월 이후: 잔여 시간 기반 점진적 조정
    from app.models.monthly_work_records import MonthlyWorkRecord

    worked_so_far = db.query(
        func.coalesce(func.sum(MonthlyWorkRecord.worked_hours), 0)
    ).filter(
        MonthlyWorkRecord.senior_id == senior_id,
        MonthlyWorkRecord.year == year,
        MonthlyWorkRecord.month < month,
        MonthlyWorkRecord.deleted_at.is_(None),
    ).scalar()

    remaining_hours = total_allocated_hours - float(worked_so_far)
    remaining_months = 11 - month + 1

    if remaining_months <= 0 or remaining_hours <= 0:
        return 0

    ideal_hours = remaining_hours / remaining_months
    ideal_rows = math.ceil(ideal_hours / session_hours)

    # 점진적 상한: 7월=+1행, 8월=+2행, ...
    max_increase = month - ADJUSTMENT_START_MONTH + 1
    allowed_max_rows = min(
        MONTHLY_DEFAULT_ROWS + max_increase,
        MONTHLY_MAX_ROWS,
    )

    return max(0, min(ideal_rows, allowed_max_rows))


# ── validate_work_feasibility ─────────────────────────────────────────────────

SESSION_MAX_HOURS = 4   # 공익활동형 기본 상한
TOTAL_DEFAULT_HOURS = 330


def validate_work_feasibility(
    session_hours: int,
    working_days: int,
    target_hours: int,
    session_max: int = SESSION_MAX_HOURS,
) -> dict:

    violations: list = []

    if session_hours > session_max:
        violations.append(f"1회 {session_hours}h → 최대 {session_max}h 초과")
        session_hours = session_max

    max_achievable = session_hours * working_days
    feasible = max_achievable >= target_hours

    suggestions: list = []
    if not feasible:
        # 대안 1: 근무 일수 늘리기
        needed_days = math.ceil(target_hours / session_hours)
        suggestions.append({
            "type": "increase_days",
            "desc": f"근무일수를 {needed_days}일로 늘리면 달성 가능",
        })

        # 대안 2: 1회 시간 늘리기
        needed_h = math.ceil(target_hours / working_days)
        if needed_h <= session_max:
            suggestions.append({
                "type": "increase_session_hours",
                "desc": f"1회 근무시간을 {needed_h}h로 늘리면 달성 가능",
            })

        # 대안 3: 어떤 조합으로도 달성 불가 (최대 시간 × 최대 일수 ≤ 목표)
        absolute_max = session_max * working_days
        if absolute_max <= target_hours:
            suggestions.append({
                "type": "unavoidable_deficit",
                "desc": f"이번 달 최대 {absolute_max}h 가능. 어르신 사정으로 인한 미달 처리.",
                "max_achievable": absolute_max,
            })

    return {
        "feasible": feasible,
        "max_achievable": max_achievable,
        "suggestions": suggestions,
        "violations": violations,
    }
