"""
BusinessUnit 스키마 검증 (BU-01 ~ BU-06)
"""
import pytest
from pydantic import ValidationError

from app.schemas.business_unit import BusinessUnitCreate, TYPE_DEFAULTS


# ── BU-01: 공익활동형 생성 — 정책 기준 자동 적용 ─────────────────────────────

def test_bu01_public_benefit_defaults():
    """공익활동형: schema 생성 성공 (시간 미입력 허용)."""
    data = BusinessUnitCreate(name="테스트사업단", type="public_benefit", year=2026)
    assert data.type.value == "public_benefit"
    assert data.monthly_default_hours is None  # 자동 적용은 service 레이어에서


# ── BU-02: 사회서비스형 생성 ──────────────────────────────────────────────────

def test_bu02_social_service():
    data = BusinessUnitCreate(name="사회서비스", type="social_service", year=2026)
    assert data.type.value == "social_service"


# ── BU-03: 시장형 — 필수 항목 미입력 시 ValidationError ─────────────────────

def test_bu03_market_missing_required():
    """시장형: 시간 항목 누락 → ValidationError."""
    with pytest.raises(ValidationError, match="시장형 필수 항목 미입력"):
        BusinessUnitCreate(name="시장형", type="market", year=2026)


# ── BU-04: 시장형 — 필수 항목 전부 입력 시 성공 ─────────────────────────────

def test_bu04_market_all_required():
    data = BusinessUnitCreate(
        name="시장형사업단", type="market", year=2026,
        monthly_default_hours=80, monthly_max_hours=80,
        total_annual_hours=880, session_default_hours=4,
    )
    assert data.monthly_default_hours == 80


# ── BU-05: TYPE_DEFAULTS 공익활동형 값 검증 ──────────────────────────────────

def test_bu05_type_defaults_public():
    defaults = TYPE_DEFAULTS["public_benefit"]
    assert defaults["monthly_default_hours"] == 30
    assert defaults["monthly_max_hours"] == 42
    assert defaults["total_annual_hours"] == 330
    assert defaults["session_max_hours"] == 4
    assert defaults["carry_over_enabled"] is True


# ── BU-06: TYPE_DEFAULTS 사회서비스형 값 검증 ────────────────────────────────

def test_bu06_type_defaults_social():
    defaults = TYPE_DEFAULTS["social_service"]
    assert defaults["monthly_default_hours"] == 60
    assert defaults["monthly_max_hours"] == 60
    assert defaults["total_annual_hours"] == 660
    assert defaults["session_max_hours"] == 8
    assert defaults["carry_over_enabled"] is False
