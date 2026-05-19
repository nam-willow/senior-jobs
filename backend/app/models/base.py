from __future__ import annotations
"""
공통 Mixin 및 SQLAlchemy 2.0 Soft Delete 자동 필터.

SoftDeleteMixin 상속 테이블:
  consultation_logs, monthly_work_records, budget_expenditures, seniors

자동 필터 우회가 필요한 경우 (감사 조회 등):
  await db.execute(select(...).execution_options(include_deleted=True))
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, event, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, Session, mapped_column, with_loader_criteria

from app.core.database import Base


# ── TimestampMixin ─────────────────────────────────────────────────────────────

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
    )


# ── SoftDeleteMixin ────────────────────────────────────────────────────────────

class SoftDeleteMixin:
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    deleted_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        default=None,
    )

    def soft_delete(self, deleted_by_id: uuid.UUID) -> None:
        self.deleted_at = datetime.now(timezone.utc)
        self.deleted_by = deleted_by_id

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


# ── Soft Delete 자동 필터 (do_orm_execute 이벤트) ──────────────────────────────
# include_deleted=True 옵션으로 우회 가능

@event.listens_for(Session, "do_orm_execute")
def _apply_soft_delete_filter(execute_state: Session) -> None:
    if (
        execute_state.is_select
        and not execute_state.is_column_load
        and not execute_state.is_relationship_load
        and not execute_state.execution_options.get("include_deleted", False)
    ):
        execute_state.statement = execute_state.statement.options(
            with_loader_criteria(
                SoftDeleteMixin,
                lambda cls: cls.deleted_at.is_(None),
                include_aliases=True,
            )
        )
