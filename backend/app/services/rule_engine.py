from __future__ import annotations
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.policy_rule import PolicyRule


class RuleEngine:
    def __init__(self, rules: list[PolicyRule]):
        self._rules = sorted(rules, key=lambda r: r.priority)

    @classmethod
    async def load(cls, db: AsyncSession, tenant_id: str) -> "RuleEngine":
        today = date.today()
        result = await db.execute(
            select(PolicyRule).where(
                PolicyRule.tenant_id == __import__("uuid").UUID(tenant_id),
                PolicyRule.is_active.is_(True),
                PolicyRule.effective_from <= today,
                (PolicyRule.effective_to.is_(None)) | (PolicyRule.effective_to >= today),
            )
        )
        rules = list(result.scalars().all())
        return cls(rules)

    def evaluate(self, context: dict) -> dict:
        applied: dict = {}
        for rule in self._rules:
            if self._match(rule.condition_json, context):
                applied.update(rule.action_json)
        return applied

    def _match(self, condition: dict, context: dict) -> bool:
        field = condition.get("field")
        op    = condition.get("operator")
        val   = condition.get("value")
        ctx_val: Any = context.get(field)

        if ctx_val is None:
            return False

        ops = {
            "eq":      lambda a, b: a == b,
            "neq":     lambda a, b: a != b,
            "gt":      lambda a, b: a > b,
            "gte":     lambda a, b: a >= b,
            "lt":      lambda a, b: a < b,
            "lte":     lambda a, b: a <= b,
            "in":      lambda a, b: a in b,
            "between": lambda a, b: b[0] <= a <= b[1],
            "contains": lambda a, b: b in a,
        }
        fn = ops.get(op)
        if fn is None:
            return False
        try:
            return fn(ctx_val, val)
        except (TypeError, KeyError):
            return False
