from __future__ import annotations
import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class PolicyRuleCreate(BaseModel):
    rule_code: str
    rule_name: str
    priority: int = 0
    effective_from: date
    effective_to: Optional[date] = None
    condition_json: dict
    action_json: dict


class PolicyRuleUpdate(BaseModel):
    rule_name: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None
    effective_to: Optional[date] = None
    condition_json: Optional[dict] = None
    action_json: Optional[dict] = None


class PolicyRuleResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    rule_code: str
    rule_name: str
    priority: int
    is_active: bool
    effective_from: date
    effective_to: Optional[date]
    condition_json: dict
    action_json: dict
    created_at: datetime

    model_config = {"from_attributes": True}
