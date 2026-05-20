from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, model_validator

from app.models.business_unit import BusinessUnitType

TYPE_DEFAULTS = {
    "public_benefit": {
        "monthly_default_hours": 30,
        "monthly_max_hours": 42,
        "total_annual_hours": 330,
        "session_default_hours": 3,
        "session_max_hours": 4,
        "carry_over_enabled": True,
    },
    "social_service": {
        "monthly_default_hours": 60,
        "monthly_max_hours": 60,
        "total_annual_hours": 660,
        "session_default_hours": 3,
        "session_max_hours": 8,
        "carry_over_enabled": False,
    },
}


class BusinessUnitCreate(BaseModel):
    name: str
    type: BusinessUnitType
    year: int
    description: Optional[str] = None
    # 시장형 필수 항목
    monthly_default_hours: Optional[int] = None
    monthly_max_hours: Optional[int] = None
    total_annual_hours: Optional[int] = None
    session_default_hours: Optional[int] = None
    session_max_hours: Optional[int] = None
    carry_over_enabled: Optional[bool] = None

    @model_validator(mode="after")
    def validate_market_required(self) -> "BusinessUnitCreate":
        if self.type == BusinessUnitType.MARKET:
            required = ["monthly_default_hours", "monthly_max_hours",
                        "total_annual_hours", "session_default_hours"]
            missing = [f for f in required if getattr(self, f) is None]
            if missing:
                raise ValueError(f"시장형 필수 항목 미입력: {missing}")
        return self


class BusinessUnitUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    # 시장형만 수정 허용
    monthly_default_hours: Optional[int] = None
    monthly_max_hours: Optional[int] = None
    total_annual_hours: Optional[int] = None
    session_default_hours: Optional[int] = None


class BusinessUnitResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    type: BusinessUnitType
    year: int
    monthly_default_hours: int
    monthly_max_hours: int
    total_annual_hours: int
    session_default_hours: int
    session_max_hours: int
    carry_over_enabled: bool
    description: Optional[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
