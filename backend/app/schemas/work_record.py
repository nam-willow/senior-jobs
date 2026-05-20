from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator

from app.models.monthly_work_records import WorkRecordStatus

MONTHLY_MAX_HARD = 43.0   # 이 이상이면 422
MONTHLY_MAX_SOFT = 42.0   # 이 이상이면 경고 + overtime_reason 필수


class WorkRecordCreate(BaseModel):
    senior_id: uuid.UUID
    year: int
    month: int
    worked_hours: float
    worked_days: int
    amount_paid: int
    overtime_reason: Optional[str] = None

    @field_validator("month")
    @classmethod
    def validate_month(cls, v: int) -> int:
        if not (1 <= v <= 11):
            raise ValueError("11월까지만 입력 가능")
        return v

    @field_validator("worked_hours")
    @classmethod
    def validate_hours(cls, v: float) -> float:
        if v > MONTHLY_MAX_HARD:
            raise ValueError(f"월 근무시간 {MONTHLY_MAX_HARD}시간 초과 저장 불가")
        return v


class WorkRecordUpdate(BaseModel):
    worked_hours: Optional[float] = None
    worked_days: Optional[int] = None
    amount_paid: Optional[int] = None
    overtime_reason: Optional[str] = None

    @field_validator("worked_hours")
    @classmethod
    def validate_hours(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v > MONTHLY_MAX_HARD:
            raise ValueError(f"월 근무시간 {MONTHLY_MAX_HARD}시간 초과 저장 불가")
        return v


class WorkRecordReject(BaseModel):
    reject_reason: str


class WorkRecordResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    senior_id: uuid.UUID
    year: int
    month: int
    worked_hours: float
    worked_days: int
    amount_paid: int
    status: WorkRecordStatus
    approved_by: Optional[uuid.UUID]
    approved_at: Optional[datetime]
    reject_reason: Optional[str]
    overtime_reason: Optional[str]
    created_by: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class MonthlyRowsResponse(BaseModel):
    senior_id: uuid.UUID
    year: int
    month: int
    recommended_rows: int
