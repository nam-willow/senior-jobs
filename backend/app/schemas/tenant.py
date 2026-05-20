from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TenantCreate(BaseModel):
    tenant_code: str
    name: str
    business_number: Optional[str] = None
    subscription_plan: str = "basic"


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    business_number: Optional[str] = None
    subscription_plan: Optional[str] = None
    is_active: Optional[bool] = None


class TenantResponse(BaseModel):
    id: uuid.UUID
    tenant_code: str
    name: str
    business_number: Optional[str]
    subscription_plan: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
