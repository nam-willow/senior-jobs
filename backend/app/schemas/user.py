from __future__ import annotations
import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr

from app.models.user import UserRole


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: UserRole
    business_unit_ids: List[uuid.UUID] = []


class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    business_unit_ids: Optional[List[uuid.UUID]] = None


class UserResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    email: str
    role: UserRole
    is_active: bool
    last_login_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}
