"""initial schema: 15 tables + RLS

Revision ID: 0001
Revises:
Create Date: 2026-05-14
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
    -- ── ENUM 타입 ─────────────────────────────────────────────────────────────
    CREATE TYPE userrole AS ENUM (
        'platform_admin','tenant_admin','social_worker','approver','auditor','viewer'
    );
    CREATE TYPE businessunittype AS ENUM ('public_benefit','social_service','market');
    CREATE TYPE budgetcategory   AS ENUM ('wage','manager_wage','operation');
    CREATE TYPE workrecordstatus AS ENUM ('DRAFT','SUBMITTED','APPROVED','REJECTED');
    CREATE TYPE consultationmethod AS ENUM ('phone','visit','in_person','other');
    CREATE TYPE filetype         AS ENUM ('excel','pdf');
    CREATE TYPE documenttype     AS ENUM ('work_log','consultation_log');

    -- ── 1. tenants ─────────────────────────────────────────────────────────────
    CREATE TABLE tenants (
        id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_code       VARCHAR(50) NOT NULL UNIQUE,
        name              VARCHAR(100) NOT NULL,
        business_number   VARCHAR(30),
        subscription_plan VARCHAR(30)  NOT NULL DEFAULT 'basic',
        is_active         BOOLEAN     NOT NULL DEFAULT TRUE,
        created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    -- ── 2. users ───────────────────────────────────────────────────────────────
    CREATE TABLE users (
        id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id     UUID        NOT NULL,
        name          VARCHAR(50) NOT NULL,
        email         VARCHAR(100) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        role          userrole    NOT NULL,
        is_active     BOOLEAN     NOT NULL DEFAULT TRUE,
        last_login_at TIMESTAMPTZ,
        created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at    TIMESTAMPTZ
    );
    CREATE INDEX ix_users_tenant_id ON users (tenant_id);
    CREATE INDEX ix_users_email     ON users (email);
    ALTER TABLE users ADD CONSTRAINT fk_users_tenant_id
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE RESTRICT;

    -- ── 3. business_units ──────────────────────────────────────────────────────
    CREATE TABLE business_units (
        id                   UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id            UUID            NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
        name                 VARCHAR(100)    NOT NULL,
        type                 businessunittype NOT NULL,
        year                 INTEGER         NOT NULL,
        monthly_default_hours INTEGER        NOT NULL,
        monthly_max_hours    INTEGER         NOT NULL,
        total_annual_hours   INTEGER         NOT NULL,
        session_default_hours INTEGER        NOT NULL,
        session_max_hours    INTEGER         NOT NULL,
        carry_over_enabled   BOOLEAN         NOT NULL DEFAULT FALSE,
        description          TEXT,
        is_active            BOOLEAN         NOT NULL DEFAULT TRUE,
        created_at           TIMESTAMPTZ     NOT NULL DEFAULT NOW()
    );
    CREATE INDEX ix_business_units_tenant_id ON business_units (tenant_id);

    -- ── 4. user_business_units (N:M) ──────────────────────────────────────────
    CREATE TABLE user_business_units (
        user_id          UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        business_unit_id UUID        NOT NULL REFERENCES business_units(id) ON DELETE CASCADE,
        assigned_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        PRIMARY KEY (user_id, business_unit_id)
    );

    -- ── 5. annual_budgets ──────────────────────────────────────────────────────
    CREATE TABLE annual_budgets (
        id                   UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id            UUID    NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
        business_unit_id     UUID    NOT NULL REFERENCES business_units(id) ON DELETE RESTRICT,
        year                 INTEGER NOT NULL,
        total_wage_budget    BIGINT  NOT NULL,
        manager_wage_budget  BIGINT  NOT NULL,
        operation_budget     BIGINT  NOT NULL,
        senior_count         INTEGER NOT NULL,
        created_by           UUID    NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
        created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at           TIMESTAMPTZ,
        CONSTRAINT uq_annual_budgets_unit_year UNIQUE (business_unit_id, year)
    );
    CREATE INDEX ix_annual_budgets_tenant_id ON annual_budgets (tenant_id);

    -- ── 6. seniors ─────────────────────────────────────────────────────────────
    CREATE TABLE seniors (
        id                    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id             UUID        NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
        business_unit_id      UUID        NOT NULL REFERENCES business_units(id) ON DELETE RESTRICT,
        name                  VARCHAR(50) NOT NULL,
        birth_date            DATE        NOT NULL,
        workplace             VARCHAR(100) DEFAULT '',
        allocated_hours       INTEGER     NOT NULL,
        hourly_wage           INTEGER     NOT NULL,
        default_session_hours INTEGER     NOT NULL DEFAULT 3,
        is_active             BOOLEAN     NOT NULL DEFAULT TRUE,
        notes                 TEXT,
        created_by            UUID        NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
        created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at            TIMESTAMPTZ,
        deleted_at            TIMESTAMPTZ,
        deleted_by            UUID        REFERENCES users(id) ON DELETE SET NULL
    );
    CREATE INDEX ix_seniors_tenant_id ON seniors (tenant_id);

    -- ── 7. budget_expenditures ─────────────────────────────────────────────────
    CREATE TABLE budget_expenditures (
        id               UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id        UUID           NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
        annual_budget_id UUID           NOT NULL REFERENCES annual_budgets(id) ON DELETE RESTRICT,
        category         budgetcategory NOT NULL,
        item_name        VARCHAR(100)   NOT NULL,
        amount           BIGINT         NOT NULL,
        expense_date     DATE           NOT NULL,
        note             TEXT,
        created_by       UUID           NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
        created_at       TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
        deleted_at       TIMESTAMPTZ,
        deleted_by       UUID           REFERENCES users(id) ON DELETE SET NULL
    );
    CREATE INDEX ix_budget_expenditures_tenant_id ON budget_expenditures (tenant_id);

    -- ── 8. monthly_work_records ────────────────────────────────────────────────
    CREATE TABLE monthly_work_records (
        id             UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id      UUID             NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
        senior_id      UUID             NOT NULL REFERENCES seniors(id) ON DELETE RESTRICT,
        year           INTEGER          NOT NULL,
        month          INTEGER          NOT NULL CHECK (month >= 1 AND month <= 11),
        worked_hours   NUMERIC(5,1)     NOT NULL CHECK (worked_hours <= 42),
        worked_days    INTEGER          NOT NULL,
        amount_paid    BIGINT           NOT NULL,
        status         workrecordstatus NOT NULL DEFAULT 'DRAFT',
        approved_by    UUID             REFERENCES users(id) ON DELETE SET NULL,
        approved_at    TIMESTAMPTZ,
        reject_reason  TEXT,
        overtime_reason TEXT,
        created_by     UUID             NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
        created_at     TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
        updated_at     TIMESTAMPTZ,
        deleted_at     TIMESTAMPTZ,
        deleted_by     UUID             REFERENCES users(id) ON DELETE SET NULL
    );
    CREATE INDEX ix_monthly_work_records_tenant_id ON monthly_work_records (tenant_id);
    CREATE INDEX ix_monthly_work_records_senior_id ON monthly_work_records (senior_id);
    CREATE UNIQUE INDEX uq_work_record_active
        ON monthly_work_records (senior_id, year, month) WHERE deleted_at IS NULL;

    -- ── 9. consultation_logs ───────────────────────────────────────────────────
    CREATE TABLE consultation_logs (
        id                    UUID               PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id             UUID               NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
        senior_id             UUID               NOT NULL REFERENCES seniors(id) ON DELETE RESTRICT,
        social_worker_id      UUID               NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
        consultation_date     TIMESTAMPTZ        NOT NULL,
        method                consultationmethod NOT NULL,
        content               TEXT               NOT NULL,
        memo                  TEXT,
        default_session_hours INTEGER            NOT NULL,
        created_at            TIMESTAMPTZ        NOT NULL DEFAULT NOW(),
        updated_at            TIMESTAMPTZ,
        deleted_at            TIMESTAMPTZ,
        deleted_by            UUID               REFERENCES users(id) ON DELETE SET NULL
    );
    CREATE INDEX ix_consultation_logs_tenant_id ON consultation_logs (tenant_id);
    CREATE INDEX ix_consultation_logs_senior_id ON consultation_logs (senior_id);

    -- ── 10. audit_logs ─────────────────────────────────────────────────────────
    CREATE TABLE audit_logs (
        id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id    UUID        NOT NULL,
        user_id      UUID        NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
        action_type  VARCHAR(50) NOT NULL,
        target_table VARCHAR(100) NOT NULL,
        target_id    UUID,
        before_data  JSONB,
        after_data   JSONB,
        ip_address   VARCHAR(50) NOT NULL,
        user_agent   TEXT,
        created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX ix_audit_logs_tenant_id ON audit_logs (tenant_id);
    CREATE INDEX ix_audit_logs_user_id   ON audit_logs (user_id);

    -- ── 11. policy_rules ───────────────────────────────────────────────────────
    CREATE TABLE policy_rules (
        id             UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id      UUID    NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
        rule_code      VARCHAR(100) NOT NULL,
        rule_name      VARCHAR(100) NOT NULL,
        priority       INTEGER NOT NULL DEFAULT 0,
        is_active      BOOLEAN NOT NULL DEFAULT TRUE,
        effective_from DATE    NOT NULL,
        effective_to   DATE,
        condition_json JSONB   NOT NULL,
        action_json    JSONB   NOT NULL,
        created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX ix_policy_rules_tenant_id ON policy_rules (tenant_id);

    -- ── 12. policy_versions ────────────────────────────────────────────────────
    CREATE TABLE policy_versions (
        id             UUID  PRIMARY KEY DEFAULT gen_random_uuid(),
        policy_rule_id UUID  NOT NULL REFERENCES policy_rules(id) ON DELETE RESTRICT,
        tenant_id      UUID  NOT NULL,
        snapshot_json  JSONB NOT NULL,
        changed_by     UUID  NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
        created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    -- ── 13. document_snapshots ─────────────────────────────────────────────────
    CREATE TABLE document_snapshots (
        id             UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id      UUID         NOT NULL,
        document_type  documenttype NOT NULL,
        reference_id   UUID         NOT NULL,
        snapshot_data  JSONB        NOT NULL,
        created_by     UUID         NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
        created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW()
    );
    CREATE INDEX ix_document_snapshots_tenant_id ON document_snapshots (tenant_id);

    -- ── 14. generated_files ────────────────────────────────────────────────────
    CREATE TABLE generated_files (
        id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id            UUID        NOT NULL,
        file_type            filetype    NOT NULL,
        file_path            VARCHAR(500) NOT NULL,
        file_hash            VARCHAR(64) NOT NULL,
        document_snapshot_id UUID        REFERENCES document_snapshots(id) ON DELETE SET NULL,
        created_by           UUID        NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
        created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX ix_generated_files_tenant_id ON generated_files (tenant_id);

    -- ── 15. tenant_settings ────────────────────────────────────────────────────
    CREATE TABLE tenant_settings (
        id            UUID  PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id     UUID  NOT NULL UNIQUE REFERENCES tenants(id) ON DELETE RESTRICT,
        settings_json JSONB NOT NULL,
        updated_by    UUID  NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
        updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    -- ── RLS 정책 ───────────────────────────────────────────────────────────────
    ALTER TABLE tenants            ENABLE ROW LEVEL SECURITY;
    ALTER TABLE tenants            FORCE  ROW LEVEL SECURITY;
    ALTER TABLE users              ENABLE ROW LEVEL SECURITY;
    ALTER TABLE users              FORCE  ROW LEVEL SECURITY;
    ALTER TABLE business_units     ENABLE ROW LEVEL SECURITY;
    ALTER TABLE business_units     FORCE  ROW LEVEL SECURITY;
    ALTER TABLE annual_budgets     ENABLE ROW LEVEL SECURITY;
    ALTER TABLE annual_budgets     FORCE  ROW LEVEL SECURITY;
    ALTER TABLE budget_expenditures ENABLE ROW LEVEL SECURITY;
    ALTER TABLE budget_expenditures FORCE  ROW LEVEL SECURITY;
    ALTER TABLE seniors            ENABLE ROW LEVEL SECURITY;
    ALTER TABLE seniors            FORCE  ROW LEVEL SECURITY;
    ALTER TABLE monthly_work_records ENABLE ROW LEVEL SECURITY;
    ALTER TABLE monthly_work_records FORCE  ROW LEVEL SECURITY;
    ALTER TABLE consultation_logs  ENABLE ROW LEVEL SECURITY;
    ALTER TABLE consultation_logs  FORCE  ROW LEVEL SECURITY;
    ALTER TABLE policy_rules       ENABLE ROW LEVEL SECURITY;
    ALTER TABLE policy_rules       FORCE  ROW LEVEL SECURITY;
    ALTER TABLE document_snapshots ENABLE ROW LEVEL SECURITY;
    ALTER TABLE document_snapshots FORCE  ROW LEVEL SECURITY;
    ALTER TABLE generated_files    ENABLE ROW LEVEL SECURITY;
    ALTER TABLE generated_files    FORCE  ROW LEVEL SECURITY;
    ALTER TABLE tenant_settings    ENABLE ROW LEVEL SECURITY;
    ALTER TABLE tenant_settings    FORCE  ROW LEVEL SECURITY;
    ALTER TABLE audit_logs         ENABLE ROW LEVEL SECURITY;
    ALTER TABLE audit_logs         FORCE  ROW LEVEL SECURITY;

    CREATE POLICY tenant_isolation ON tenants
        USING (current_setting('app.current_tenant', true) = 'ALL'
               OR id::text = current_setting('app.current_tenant', true));

    CREATE POLICY tenant_isolation ON users
        USING (current_setting('app.current_tenant', true) = 'ALL'
               OR tenant_id::text = current_setting('app.current_tenant', true));

    CREATE POLICY tenant_isolation ON business_units
        USING (current_setting('app.current_tenant', true) = 'ALL'
               OR tenant_id::text = current_setting('app.current_tenant', true));

    CREATE POLICY tenant_isolation ON annual_budgets
        USING (current_setting('app.current_tenant', true) = 'ALL'
               OR tenant_id::text = current_setting('app.current_tenant', true));

    CREATE POLICY tenant_isolation ON budget_expenditures
        USING (current_setting('app.current_tenant', true) = 'ALL'
               OR tenant_id::text = current_setting('app.current_tenant', true));

    CREATE POLICY tenant_isolation ON seniors
        USING (current_setting('app.current_tenant', true) = 'ALL'
               OR tenant_id::text = current_setting('app.current_tenant', true));

    CREATE POLICY tenant_isolation ON monthly_work_records
        USING (current_setting('app.current_tenant', true) = 'ALL'
               OR tenant_id::text = current_setting('app.current_tenant', true));

    CREATE POLICY tenant_isolation ON consultation_logs
        USING (current_setting('app.current_tenant', true) = 'ALL'
               OR tenant_id::text = current_setting('app.current_tenant', true));

    CREATE POLICY tenant_isolation ON policy_rules
        USING (current_setting('app.current_tenant', true) = 'ALL'
               OR tenant_id::text = current_setting('app.current_tenant', true));

    CREATE POLICY tenant_isolation ON document_snapshots
        USING (current_setting('app.current_tenant', true) = 'ALL'
               OR tenant_id::text = current_setting('app.current_tenant', true));

    CREATE POLICY tenant_isolation ON generated_files
        USING (current_setting('app.current_tenant', true) = 'ALL'
               OR tenant_id::text = current_setting('app.current_tenant', true));

    CREATE POLICY tenant_isolation ON tenant_settings
        USING (current_setting('app.current_tenant', true) = 'ALL'
               OR tenant_id::text = current_setting('app.current_tenant', true));

    CREATE POLICY tenant_isolation ON audit_logs
        USING (current_setting('app.current_tenant', true) = 'ALL'
               OR tenant_id::text = current_setting('app.current_tenant', true));
    """)


def downgrade() -> None:
    op.execute("""
    DROP TABLE IF EXISTS tenant_settings, generated_files, document_snapshots,
        policy_versions, policy_rules, audit_logs, consultation_logs,
        monthly_work_records, budget_expenditures, seniors, annual_budgets,
        user_business_units, business_units, users, tenants CASCADE;

    DROP TYPE IF EXISTS userrole, businessunittype, budgetcategory,
        workrecordstatus, consultationmethod, filetype, documenttype;
    """)
