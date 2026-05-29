from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AnnualBudget(Base):
    __tablename__ = "annual_budgets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    business_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("business_units.id", ondelete="RESTRICT"),
        nullable=False,
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    total_wage_budget: Mapped[int] = mapped_column(BigInteger, nullable=False)
    manager_wage_budget: Mapped[int] = mapped_column(BigInteger, nullable=False)
    operation_budget: Mapped[int] = mapped_column(BigInteger, nullable=False)
    senior_count: Mapped[int] = mapped_column(Integer, nullable=False)
    # 연초 예산 편성 시 입력하는 계획 시급. 어르신 임금 예산 검증의 기준값.
    # (근무일지 자동계산은 Senior.hourly_wage를 사용 — 별개 값)
    hourly_wage: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
