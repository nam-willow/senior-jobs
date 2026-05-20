from __future__ import annotations
import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin


class BusinessUnitType(str, enum.Enum):
    PUBLIC_BENEFIT  = "public_benefit"
    SOCIAL_SERVICE  = "social_service"
    MARKET          = "market"


class BusinessUnit(Base, TimestampMixin):
    __tablename__ = "business_units"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[BusinessUnitType] = mapped_column(
        SAEnum(BusinessUnitType, name="businessunittype", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    monthly_default_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    monthly_max_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    total_annual_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    session_default_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    session_max_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    carry_over_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
