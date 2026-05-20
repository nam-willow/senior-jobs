"""
RuleEngine 단위 테스트 (RE-01 ~ RE-08)
"""
from unittest.mock import MagicMock

import pytest

from app.models.policy_rule import PolicyRule
from app.services.rule_engine import RuleEngine


def _rule(condition_json, action_json, priority=0, is_active=True):
    r = MagicMock(spec=PolicyRule)
    r.priority = priority
    r.is_active = is_active
    r.condition_json = condition_json
    r.action_json = action_json
    return r


# ── RE-01: eq 연산자 ─────────────────────────────────────────────────────────

def test_re01_eq_match():
    """field=type, operator=eq, value='public_benefit' → 매칭."""
    engine = RuleEngine([
        _rule({"field": "type", "operator": "eq", "value": "public_benefit"},
              {"session_max": 4})
    ])
    result = engine.evaluate({"type": "public_benefit"})
    assert result == {"session_max": 4}


def test_re02_eq_no_match():
    """field 값 불일치 → 빈 dict."""
    engine = RuleEngine([
        _rule({"field": "type", "operator": "eq", "value": "market"},
              {"session_max": 8})
    ])
    result = engine.evaluate({"type": "public_benefit"})
    assert result == {}


# ── RE-03: gte/lte ────────────────────────────────────────────────────────────

def test_re03_gte_match():
    """month >= 7 → 매칭."""
    engine = RuleEngine([
        _rule({"field": "month", "operator": "gte", "value": 7},
              {"monthly_max_hours": 42})
    ])
    assert engine.evaluate({"month": 7}) == {"monthly_max_hours": 42}
    assert engine.evaluate({"month": 11}) == {"monthly_max_hours": 42}


def test_re04_lte_no_match():
    """month <= 6, context month=7 → 불일치."""
    engine = RuleEngine([
        _rule({"field": "month", "operator": "lte", "value": 6},
              {"fixed_rows": 10})
    ])
    assert engine.evaluate({"month": 7}) == {}


# ── RE-05: between ────────────────────────────────────────────────────────────

def test_re05_between():
    """42 between [42, 43] → 매칭."""
    engine = RuleEngine([
        _rule({"field": "worked_hours", "operator": "between", "value": [42, 43]},
              {"warning": True})
    ])
    assert engine.evaluate({"worked_hours": 42}) == {"warning": True}
    assert engine.evaluate({"worked_hours": 42.5}) == {"warning": True}
    assert engine.evaluate({"worked_hours": 40}) == {}


# ── RE-06: in ─────────────────────────────────────────────────────────────────

def test_re06_in():
    """type in ['social_service', 'market'] → 매칭."""
    engine = RuleEngine([
        _rule({"field": "type", "operator": "in", "value": ["social_service", "market"]},
              {"labor_law_applies": True})
    ])
    assert engine.evaluate({"type": "social_service"}) == {"labor_law_applies": True}
    assert engine.evaluate({"type": "market"}) == {"labor_law_applies": True}
    assert engine.evaluate({"type": "public_benefit"}) == {}


# ── RE-07: 우선순위 — 마지막 규칙이 덮어씀 ──────────────────────────────────

def test_re07_priority_last_wins():
    """동일 action 키: priority 낮은 쪽 먼저, 높은 쪽이 덮어씀."""
    engine = RuleEngine([
        _rule({"field": "x", "operator": "eq", "value": 1}, {"limit": 10}, priority=0),
        _rule({"field": "x", "operator": "eq", "value": 1}, {"limit": 20}, priority=1),
    ])
    result = engine.evaluate({"x": 1})
    assert result["limit"] == 20


# ── RE-08: 알 수 없는 연산자 ─────────────────────────────────────────────────

def test_re08_unknown_operator():
    """지원하지 않는 operator → False → 매칭 안 됨."""
    engine = RuleEngine([
        _rule({"field": "x", "operator": "INVALID_OP", "value": 1}, {"hit": True})
    ])
    assert engine.evaluate({"x": 1}) == {}
