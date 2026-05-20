from __future__ import annotations
import enum
import uuid
from datetime import date
from typing import Optional

from sqlalchemy import BigInteger, Date, Enum as SAEnum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import SoftDeleteMixin, TimestampMixin


class BudgetCategory(str, enum.Enum):
    WAGE         = "wage"
    MANAGER_WAGE = "manager_wage"
    OPERATION    = "operation"


class BudgetExpenditure(Base, SoftDeleteMixin, TimestampMixin):
    __tablename__ = "budget_expenditures"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    annual_budget_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("annual_budgets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    category: Mapped[BudgetCategory] = mapped_column(
        SAEnum(BudgetCategory, name="budgetcategory", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    item_name: Mapped[str] = mapped_column(String(100), nullable=False)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
