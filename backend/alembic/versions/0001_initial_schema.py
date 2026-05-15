"""initial schema: 15 tables + RLS

Revision ID: 0001
Revises:
Create Date: 2026-05-13
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── ENUM 타입 먼저 생성 ────────────────────────────────────────────────────
    op.execute("CREATE TYPE userrole AS ENUM ('platform_admin','tenant_admin','social_worker','approver','auditor','viewer')")
    op.execute("CREATE TYPE businessunittype AS ENUM ('public_benefit','social_service','market')")
    op.execute("CREATE TYPE budgetcategory AS ENUM ('wage','manager_wage','operation')")
    op.execute("CREATE TYPE workrecordstatus AS ENUM ('DRAFT','SUBMITTED','APPROVED','REJECTED')")
    op.execute("CREATE TYPE consultationmethod AS ENUM ('phone','visit','in_person','other')")
    op.execute("CREATE TYPE filetype AS ENUM ('excel','pdf')")
    op.execute("CREATE TYPE documenttype AS ENUM ('work_log','consultation_log')")

    # ── 1. tenants ────────────────────────────────────────────────────────────
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_code", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("business_number", sa.String(30), nullable=True),
        sa.Column("subscription_plan", sa.String(30), nullable=False, server_default="basic"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    # ── 2. users ──────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("email", sa.String(100), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("platform_admin","tenant_admin","social_worker","approver","auditor","viewer", name="userrole", create_type=False), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT", use_alter=True, name="fk_users_tenant_id"),
    )
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])
    op.create_index("ix_users_email", "users", ["email"])

    # ── 3. business_units ─────────────────────────────────────────────────────
    op.create_table(
        "business_units",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("type", sa.Enum("public_benefit","social_service","market", name="businessunittype", create_type=False), nullable=False),
        sa.Column("year", sa.Integer, nullable=False),
        sa.Column("monthly_default_hours", sa.Integer, nullable=False),
        sa.Column("monthly_max_hours", sa.Integer, nullable=False),
        sa.Column("total_annual_hours", sa.Integer, nullable=False),
        sa.Column("session_default_hours", sa.Integer, nullable=False),
        sa.Column("session_max_hours", sa.Integer, nullable=False),
        sa.Column("carry_over_enabled", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_business_units_tenant_id", "business_units", ["tenant_id"])

    # ── 4. user_business_units (N:M) ──────────────────────────────────────────
    op.create_table(
        "user_business_units",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_unit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("user_id", "business_unit_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["business_unit_id"], ["business_units.id"], ondelete="CASCADE"),
    )

    # ── 5. annual_budgets ─────────────────────────────────────────────────────
    op.create_table(
        "annual_budgets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_unit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("year", sa.Integer, nullable=False),
        sa.Column("total_wage_budget", sa.BigInteger, nullable=False),
        sa.Column("manager_wage_budget", sa.BigInteger, nullable=False),
        sa.Column("operation_budget", sa.BigInteger, nullable=False),
        sa.Column("senior_count", sa.Integer, nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["business_unit_id"], ["business_units.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("business_unit_id", "year", name="uq_annual_budgets_unit_year"),
    )
    op.create_index("ix_annual_budgets_tenant_id", "annual_budgets", ["tenant_id"])

    # ── 6. seniors ────────────────────────────────────────────────────────────
    op.create_table(
        "seniors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_unit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("birth_date", sa.Date, nullable=False),
        sa.Column("workplace", sa.String(100), nullable=True, server_default=""),
        sa.Column("allocated_hours", sa.Integer, nullable=False),
        sa.Column("hourly_wage", sa.Integer, nullable=False),
        sa.Column("default_session_hours", sa.Integer, nullable=False, server_default="3"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["business_unit_id"], ["business_units.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["deleted_by"], ["users.id"], ondelete="SET NULL", use_alter=True, name="fk_seniors_deleted_by"),
    )
    op.create_index("ix_seniors_tenant_id", "seniors", ["tenant_id"])

    # ── 7. budget_expenditures ────────────────────────────────────────────────
    op.create_table(
        "budget_expenditures",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("annual_budget_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", sa.Enum("wage","manager_wage","operation", name="budgetcategory", create_type=False), nullable=False),
        sa.Column("item_name", sa.String(100), nullable=False),
        sa.Column("amount", sa.BigInteger, nullable=False),
        sa.Column("expense_date", sa.Date, nullable=False),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["annual_budget_id"], ["annual_budgets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["deleted_by"], ["users.id"], ondelete="SET NULL", use_alter=True, name="fk_budget_expenditures_deleted_by"),
    )
    op.create_index("ix_budget_expenditures_tenant_id", "budget_expenditures", ["tenant_id"])

    # ── 8. monthly_work_records ───────────────────────────────────────────────
    op.create_table(
        "monthly_work_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("senior_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("year", sa.Integer, nullable=False),
        sa.Column("month", sa.Integer, nullable=False),
        sa.Column("worked_hours", sa.Numeric(5, 1), nullable=False),
        sa.Column("worked_days", sa.Integer, nullable=False),
        sa.Column("amount_paid", sa.BigInteger, nullable=False),
        sa.Column("status", sa.Enum("DRAFT","SUBMITTED","APPROVED","REJECTED", name="workrecordstatus", create_type=False), nullable=False, server_default="DRAFT"),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reject_reason", sa.Text, nullable=True),
        sa.Column("overtime_reason", sa.Text, nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["senior_id"], ["seniors.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["deleted_by"], ["users.id"], ondelete="SET NULL", use_alter=True, name="fk_work_records_deleted_by"),
    )
    op.create_index("ix_monthly_work_records_tenant_id", "monthly_work_records", ["tenant_id"])
    op.create_index("ix_monthly_work_records_senior_id", "monthly_work_records", ["senior_id"])
    # CHECK: 1 ≤ month ≤ 11
    op.execute("ALTER TABLE monthly_work_records ADD CONSTRAINT ck_month_range CHECK (month >= 1 AND month <= 11)")
    # CHECK: worked_hours ≤ 42
    op.execute("ALTER TABLE monthly_work_records ADD CONSTRAINT ck_worked_hours_max CHECK (worked_hours <= 42)")
    # UNIQUE: (senior_id, year, month) WHERE deleted_at IS NULL
    op.execute("CREATE UNIQUE INDEX uq_work_record_active ON monthly_work_records (senior_id, year, month) WHERE deleted_at IS NULL")

    # ── 9. consultation_logs ──────────────────────────────────────────────────
    op.create_table(
        "consultation_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("senior_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("social_worker_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("consultation_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("method", sa.Enum("phone","visit","in_person","other", name="consultationmethod", create_type=False), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("memo", sa.Text, nullable=True),
        sa.Column("default_session_hours", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["senior_id"], ["seniors.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["social_worker_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["deleted_by"], ["users.id"], ondelete="SET NULL", use_alter=True, name="fk_consultation_logs_deleted_by"),
    )
    op.create_index("ix_consultation_logs_tenant_id", "consultation_logs", ["tenant_id"])
    op.create_index("ix_consultation_logs_senior_id", "consultation_logs", ["senior_id"])

    # ── 10. audit_logs ────────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_type", sa.String(50), nullable=False),
        sa.Column("target_table", sa.String(100), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("before_data", postgresql.JSONB, nullable=True),
        sa.Column("after_data", postgresql.JSONB, nullable=True),
        sa.Column("ip_address", sa.String(50), nullable=False),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_audit_logs_tenant_id", "audit_logs", ["tenant_id"])
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])

    # ── 11. policy_rules ──────────────────────────────────────────────────────
    op.create_table(
        "policy_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_code", sa.String(100), nullable=False),
        sa.Column("rule_name", sa.String(100), nullable=False),
        sa.Column("priority", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("effective_from", sa.Date, nullable=False),
        sa.Column("effective_to", sa.Date, nullable=True),
        sa.Column("condition_json", postgresql.JSONB, nullable=False),
        sa.Column("action_json", postgresql.JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_policy_rules_tenant_id", "policy_rules", ["tenant_id"])

    # ── 12. policy_versions ───────────────────────────────────────────────────
    op.create_table(
        "policy_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("policy_rule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_json", postgresql.JSONB, nullable=False),
        sa.Column("changed_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["policy_rule_id"], ["policy_rules.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["changed_by"], ["users.id"], ondelete="RESTRICT"),
    )

    # ── 13. document_snapshots ────────────────────────────────────────────────
    op.create_table(
        "document_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_type", sa.Enum("work_log","consultation_log", name="documenttype", create_type=False), nullable=False),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_data", postgresql.JSONB, nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_document_snapshots_tenant_id", "document_snapshots", ["tenant_id"])

    # ── 14. generated_files ───────────────────────────────────────────────────
    op.create_table(
        "generated_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_type", sa.Enum("excel","pdf", name="filetype", create_type=False), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("document_snapshot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["document_snapshot_id"], ["document_snapshots.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_generated_files_tenant_id", "generated_files", ["tenant_id"])

    # ── 15. tenant_settings ───────────────────────────────────────────────────
    op.create_table(
        "tenant_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("settings_json", postgresql.JSONB, nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="RESTRICT"),
    )

    # ── RLS 정책 ──────────────────────────────────────────────────────────────
    _rls_tables = [
        "tenants",
        "users",
        "business_units",
        "annual_budgets",
        "budget_expenditures",
        "seniors",
        "monthly_work_records",
        "consultation_logs",
        "policy_rules",
        "document_snapshots",
        "generated_files",
        "tenant_settings",
    ]

    for table in _rls_tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (
                current_setting('app.current_tenant', true) = 'ALL'
                OR tenant_id::text = current_setting('app.current_tenant', true)
            )
        """)

    # audit_logs, policy_versions, user_business_units: tenant_id 컬럼 있으나 RLS 방식 상이
    op.execute("ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON audit_logs
        USING (
            current_setting('app.current_tenant', true) = 'ALL'
            OR tenant_id::text = current_setting('app.current_tenant', true)
        )
    """)


def downgrade() -> None:
    tables = [
        "tenant_settings", "generated_files", "document_snapshots",
        "policy_versions", "policy_rules", "audit_logs",
        "consultation_logs", "monthly_work_records", "budget_expenditures",
        "seniors", "annual_budgets", "user_business_units",
        "business_units", "users", "tenants",
    ]
    for table in tables:
        op.drop_table(table)

    for enum_name in ["userrole","businessunittype","budgetcategory","workrecordstatus","consultationmethod","filetype","documenttype"]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
