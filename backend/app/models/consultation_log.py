from __future__ import annotations
import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import SoftDeleteMixin, TimestampMixin


class ConsultationMethod(str, enum.Enum):
    PHONE     = "phone"
    VISIT     = "visit"
    IN_PERSON = "in_person"
    OTHER     = "other"


class ConsultationLog(Base, SoftDeleteMixin, TimestampMixin):
    __tablename__ = "consultation_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    senior_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("seniors.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    social_worker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    consultation_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    method: Mapped[ConsultationMethod] = mapped_column(
        SAEnum(ConsultationMethod, name="consultationmethod", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    memo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    default_session_hours: Mapped[int] = mapped_column(Integer, nullable=False)
