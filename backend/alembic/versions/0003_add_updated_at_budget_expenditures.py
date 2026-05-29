"""budget_expenditures 테이블에 updated_at 컬럼 추가

0001 초기 마이그레이션에서 budget_expenditures 테이블만 updated_at 컬럼이 누락됨.
모델(BudgetExpenditure)은 TimestampMixin을 상속해 updated_at을 기대하므로
SELECT 시 UndefinedColumnError(500)가 발생했음. 다른 테이블과 정합성을 맞춤.

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-29
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "budget_expenditures",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("budget_expenditures", "updated_at")
