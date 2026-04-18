"""Phase 3 schema additions: evidence_controls, policies, access reviews, personnel, risks.

Revision ID: 20260416_000003
Revises: 20260415_000002
Create Date: 2026-04-16 00:00:00
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import inspect


revision = "20260416_000003"
down_revision = "20260415_000002"
branch_labels = None
depends_on = None


def _table_names() -> set[str]:
    bind = op.get_bind()
    return set(inspect(bind).get_table_names())


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    id_type = "SERIAL PRIMARY KEY" if dialect == "postgresql" else "INTEGER PRIMARY KEY AUTOINCREMENT"
    now_default = "now()" if dialect == "postgresql" else "datetime('now')"

    statements = [
        # 6.4 Evidence-to-multiple-controls junction table
        f"""
        CREATE TABLE IF NOT EXISTS evidence_controls (
            id {id_type},
            evidence_id INTEGER NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
            control_id INTEGER NOT NULL REFERENCES controls(id) ON DELETE CASCADE,
            is_primary INTEGER NOT NULL DEFAULT 0,
            mapped_by INTEGER REFERENCES users(id),
            created_at TEXT NOT NULL DEFAULT ({now_default}),
            UNIQUE(evidence_id, control_id)
        )
        """,
        # Backfill evidence_controls from existing evidence.control_id
        """
        INSERT INTO evidence_controls (evidence_id, control_id, is_primary)
        SELECT id, control_id, 1
        FROM evidence
        WHERE control_id IS NOT NULL
        ON CONFLICT (evidence_id, control_id) DO NOTHING
        """,
        # 6.5 Policy management tables
        f"""
        CREATE TABLE IF NOT EXISTS policies (
            id {id_type},
            framework_id INTEGER REFERENCES frameworks(id),
            title TEXT NOT NULL,
            description TEXT,
            policy_type TEXT,
            owner_user_id INTEGER REFERENCES users(id),
            status TEXT NOT NULL DEFAULT 'draft',
            review_frequency_days INTEGER,
            last_approved_at TEXT,
            next_review_date TEXT,
            approved_by INTEGER REFERENCES users(id),
            sharepoint_url TEXT,
            sharepoint_item_id TEXT,
            local_path TEXT,
            file_name TEXT,
            sha256_hash TEXT,
            version TEXT,
            created_at TEXT NOT NULL DEFAULT ({now_default}),
            updated_at TEXT
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS policy_controls (
            id {id_type},
            policy_id INTEGER NOT NULL REFERENCES policies(id) ON DELETE CASCADE,
            control_id INTEGER NOT NULL REFERENCES controls(id) ON DELETE CASCADE,
            UNIQUE(policy_id, control_id)
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS policy_versions (
            id {id_type},
            policy_id INTEGER NOT NULL REFERENCES policies(id) ON DELETE CASCADE,
            version TEXT,
            uploaded_by INTEGER REFERENCES users(id),
            sharepoint_item_id TEXT,
            sha256_hash TEXT,
            change_summary TEXT,
            created_at TEXT NOT NULL DEFAULT ({now_default})
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS policy_consistency_flags (
            id {id_type},
            policy_id INTEGER NOT NULL REFERENCES policies(id) ON DELETE CASCADE,
            control_id INTEGER REFERENCES controls(id),
            flag_type TEXT NOT NULL,
            severity TEXT NOT NULL DEFAULT 'warning',
            detail TEXT,
            detected_at TEXT NOT NULL DEFAULT ({now_default}),
            resolved_at TEXT,
            is_active INTEGER NOT NULL DEFAULT 1
        )
        """,
        # 6.6 Access review tables
        f"""
        CREATE TABLE IF NOT EXISTS access_reviews (
            id {id_type},
            title TEXT NOT NULL,
            system_name TEXT NOT NULL,
            integration_name TEXT,
            reviewer_user_id INTEGER REFERENCES users(id),
            assigned_by INTEGER REFERENCES users(id),
            status TEXT NOT NULL DEFAULT 'pending',
            due_date TEXT,
            completed_at TEXT,
            period_start TEXT,
            period_end TEXT,
            total_accounts INTEGER NOT NULL DEFAULT 0,
            accounts_approved INTEGER NOT NULL DEFAULT 0,
            accounts_revoked INTEGER NOT NULL DEFAULT 0,
            accounts_pending INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT ({now_default}),
            updated_at TEXT
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS access_review_accounts (
            id {id_type},
            review_id INTEGER NOT NULL REFERENCES access_reviews(id) ON DELETE CASCADE,
            external_user_id TEXT,
            email TEXT,
            display_name TEXT,
            role_in_system TEXT,
            is_admin INTEGER NOT NULL DEFAULT 0,
            employment_status TEXT DEFAULT 'unknown',
            risk_flag INTEGER NOT NULL DEFAULT 0,
            decision TEXT,
            decision_by INTEGER REFERENCES users(id),
            decision_at TEXT,
            decision_notes TEXT,
            remediation_task_id INTEGER REFERENCES tasks(id)
        )
        """,
        # 6.7 Personnel compliance tables
        f"""
        CREATE TABLE IF NOT EXISTS personnel (
            id {id_type},
            user_id INTEGER REFERENCES users(id),
            email TEXT UNIQUE NOT NULL,
            display_name TEXT,
            department TEXT,
            title TEXT,
            employment_status TEXT NOT NULL DEFAULT 'active',
            start_date TEXT,
            termination_date TEXT,
            entra_oid TEXT,
            created_at TEXT NOT NULL DEFAULT ({now_default}),
            updated_at TEXT
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS personnel_requirements (
            id {id_type},
            title TEXT NOT NULL,
            requirement_type TEXT NOT NULL,
            applies_to TEXT NOT NULL DEFAULT 'all',
            due_within_days_of_hire INTEGER,
            recurrence_days INTEGER,
            is_active INTEGER NOT NULL DEFAULT 1,
            control_id INTEGER REFERENCES controls(id)
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS personnel_compliance_records (
            id {id_type},
            personnel_id INTEGER NOT NULL REFERENCES personnel(id) ON DELETE CASCADE,
            requirement_id INTEGER NOT NULL REFERENCES personnel_requirements(id) ON DELETE CASCADE,
            status TEXT NOT NULL DEFAULT 'pending',
            completed_at TEXT,
            due_date TEXT,
            evidence_url TEXT,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT ({now_default}),
            updated_at TEXT
        )
        """,
        # 6.8 Risk register tables
        f"""
        CREATE TABLE IF NOT EXISTS risks (
            id {id_type},
            title TEXT NOT NULL,
            description TEXT,
            category TEXT,
            owner_user_id INTEGER REFERENCES users(id),
            likelihood INTEGER,
            impact INTEGER,
            risk_score INTEGER,
            inherent_risk_score INTEGER,
            residual_risk_score INTEGER,
            treatment TEXT,
            treatment_notes TEXT,
            status TEXT NOT NULL DEFAULT 'open',
            review_date TEXT,
            created_by INTEGER REFERENCES users(id),
            created_at TEXT NOT NULL DEFAULT ({now_default}),
            updated_at TEXT
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS risk_controls (
            id {id_type},
            risk_id INTEGER NOT NULL REFERENCES risks(id) ON DELETE CASCADE,
            control_id INTEGER NOT NULL REFERENCES controls(id) ON DELETE CASCADE,
            UNIQUE(risk_id, control_id)
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS risk_history (
            id {id_type},
            risk_id INTEGER NOT NULL REFERENCES risks(id) ON DELETE CASCADE,
            likelihood INTEGER,
            impact INTEGER,
            risk_score INTEGER,
            recorded_by INTEGER REFERENCES users(id),
            recorded_at TEXT NOT NULL DEFAULT ({now_default}),
            notes TEXT
        )
        """,
    ]

    tables = _table_names()
    for statement in statements:
        # Skip backfill if evidence_controls already has rows
        if "INSERT INTO evidence_controls" in statement:
            if "evidence_controls" not in tables:
                continue  # table not yet created; skip; it will be populated on next run
            bind.exec_driver_sql(statement)
        else:
            bind.exec_driver_sql(statement)


def downgrade() -> None:
    bind = op.get_bind()
    for table in [
        "risk_history",
        "risk_controls",
        "risks",
        "personnel_compliance_records",
        "personnel_requirements",
        "personnel",
        "access_review_accounts",
        "access_reviews",
        "policy_consistency_flags",
        "policy_versions",
        "policy_controls",
        "policies",
        "evidence_controls",
    ]:
        bind.exec_driver_sql(f"DROP TABLE IF EXISTS {table}")
