"""tenants 테이블에 address 컬럼 추가

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-21
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("address", sa.String(200), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tenants", "address")
