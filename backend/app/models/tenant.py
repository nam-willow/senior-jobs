from __future__ import annotations
import uuid
from typing import Optional

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    business_number: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    subscription_plan: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default="basic"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
