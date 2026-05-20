from __future__ import annotations
import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Enum as SAEnum, ForeignKey, Integer, Numeric, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import SoftDeleteMixin, TimestampMixin


class WorkRecordStatus(str, enum.Enum):
    DRAFT     = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED  = "APPROVED"
    REJECTED  = "REJECTED"


class MonthlyWorkRecord(Base, SoftDeleteMixin, TimestampMixin):
    __tablename__ = "monthly_work_records"
    __table_args__ = (
        UniqueConstraint("senior_id", "year", "month", name="uq_work_record_senior_year_month"),
    )

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
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    worked_hours: Mapped[float] = mapped_column(Numeric(5, 1), nullable=False)
    worked_days: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_paid: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[WorkRecordStatus] = mapped_column(
        SAEnum(WorkRecordStatus, name="workrecordstatus", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=WorkRecordStatus.DRAFT,
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reject_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    overtime_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
