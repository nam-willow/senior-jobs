"""annual_budgets 테이블에 hourly_wage 컬럼 추가

연초 예산 편성 시 입력하는 계획 시급. 어르신 임금 예산 검증
(시급 × 연간시간 × 인원 == 어르신 임금 예산)의 기준값.
기존 행은 server_default 0으로 채워짐.

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-29
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "annual_budgets",
        sa.Column("hourly_wage", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("annual_budgets", "hourly_wage")
