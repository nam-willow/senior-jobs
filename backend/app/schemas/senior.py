from __future__ import annotations
import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class SeniorCreate(BaseModel):
    business_unit_id: uuid.UUID
    name: str
    birth_date: date
    workplace: Optional[str] = ""
    hourly_wage: int
    default_session_hours: int = 3
    notes: Optional[str] = None


class SeniorUpdate(BaseModel):
    name: Optional[str] = None
    birth_date: Optional[date] = None
    workplace: Optional[str] = None
    hourly_wage: Optional[int] = None
    default_session_hours: Optional[int] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class SeniorResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    business_unit_id: uuid.UUID
    name: str
    birth_date: date
    workplace: Optional[str]
    allocated_hours: int
    hourly_wage: int
    default_session_hours: int
    is_active: bool
    notes: Optional[str]
    created_by: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}
