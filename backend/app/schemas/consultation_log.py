from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.consultation_log import ConsultationMethod


class ConsultationLogCreate(BaseModel):
    senior_id: uuid.UUID
    consultation_date: datetime
    method: ConsultationMethod
    content: str
    memo: Optional[str] = None
    default_session_hours: int


class ConsultationLogUpdate(BaseModel):
    consultation_date: Optional[datetime] = None
    method: Optional[ConsultationMethod] = None
    content: Optional[str] = None
    memo: Optional[str] = None


class ConsultationLogResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    senior_id: uuid.UUID
    social_worker_id: uuid.UUID
    consultation_date: datetime
    method: ConsultationMethod
    content: str
    memo: Optional[str]
    default_session_hours: int
    created_at: datetime

    model_config = {"from_attributes": True}
