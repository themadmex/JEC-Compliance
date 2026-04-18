"""Baseline schema for JEC Compliance Hub.

Revision ID: 20260313_000001
Revises:
Create Date: 2026-03-13 08:35:00
"""
from __future__ import annotations

from alembic import op


revision = "20260313_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    id_type = "SERIAL PRIMARY KEY" if dialect == "postgresql" else "INTEGER PRIMARY KEY AUTOINCREMENT"
    now_default = "now()" if dialect == "postgresql" else "datetime('now')"

    statements = [
        f"""
        CREATE TABLE IF NOT EXISTS frameworks (
            id {id_type},
            name TEXT NOT NULL,
            version TEXT NOT NULL,
            UNIQUE(name, version)
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS controls (
            id {id_type},
            framework_id INTEGER NOT NULL,
            control_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            owner TEXT,
            implementation_status TEXT NOT NULL DEFAULT 'draft',
            type1_ready INTEGER NOT NULL DEFAULT 0,
            type2_ready INTEGER NOT NULL DEFAULT 0,
            last_tested_at TEXT,
            next_review_at TEXT,
            FOREIGN KEY(framework_id) REFERENCES frameworks(id) ON DELETE CASCADE,
            UNIQUE(framework_id, control_id)
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS evidence (
            id {id_type},
            control_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            source TEXT NOT NULL,
            artifact_path TEXT NOT NULL,
            collected_at TEXT NOT NULL,
            period_start TEXT,
            period_end TEXT,
            status TEXT NOT NULL DEFAULT 'accepted',
            notes TEXT,
            submitter_id INTEGER,
            approver_id INTEGER,
            approved_at TEXT,
            rejected_reason TEXT,
            locked_at TEXT,
            sha256_hash TEXT,
            sharepoint_id TEXT,
            audit_period_id INTEGER,
            collection_due_date TEXT,
            FOREIGN KEY(control_id) REFERENCES controls(id) ON DELETE CASCADE
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS control_checks (
            id {id_type},
            control_id INTEGER NOT NULL,
            checked_at TEXT NOT NULL,
            result TEXT NOT NULL,
            details TEXT NOT NULL,
            FOREIGN KEY(control_id) REFERENCES controls(id) ON DELETE CASCADE
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS integration_runs (
            id {id_type},
            source TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT NOT NULL,
            status TEXT NOT NULL,
            details TEXT NOT NULL
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS users (
            id {id_type},
            oid TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL,
            name TEXT,
            role TEXT NOT NULL DEFAULT 'viewer',
            created_at TEXT NOT NULL DEFAULT ({now_default}),
            last_login_at TEXT NOT NULL DEFAULT ({now_default})
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS audit_log (
            id {id_type},
            actor_id INTEGER,
            action TEXT NOT NULL,
            object_type TEXT NOT NULL,
            object_id INTEGER NOT NULL,
            previous_state TEXT,
            new_state TEXT,
            created_at TEXT NOT NULL DEFAULT ({now_default}),
            FOREIGN KEY(actor_id) REFERENCES users(id)
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_audit_log_object
        ON audit_log(object_type, object_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_audit_log_actor
        ON audit_log(actor_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_audit_log_time
        ON audit_log(created_at)
        """,
    ]

    for statement in statements:
        bind.exec_driver_sql(statement)

    if dialect == "sqlite":
        for statement in [
            """
            CREATE TRIGGER IF NOT EXISTS audit_log_no_update
            BEFORE UPDATE ON audit_log
            BEGIN
                SELECT RAISE(ABORT, 'audit_log rows are immutable');
            END
            """,
            """
            CREATE TRIGGER IF NOT EXISTS audit_log_no_delete
            BEFORE DELETE ON audit_log
            BEGIN
                SELECT RAISE(ABORT, 'audit_log rows are immutable');
            END
            """,
        ]:
            bind.exec_driver_sql(statement)


def downgrade() -> None:
    bind = op.get_bind()
    statements = []
    if bind.dialect.name == "sqlite":
        statements.extend(
            [
                "DROP TRIGGER IF EXISTS audit_log_no_delete",
                "DROP TRIGGER IF EXISTS audit_log_no_update",
            ]
        )
    statements.extend(
        [
        "DROP INDEX IF EXISTS idx_audit_log_time",
        "DROP INDEX IF EXISTS idx_audit_log_actor",
        "DROP INDEX IF EXISTS idx_audit_log_object",
        "DROP TABLE IF EXISTS audit_log",
        "DROP TABLE IF EXISTS control_checks",
        "DROP TABLE IF EXISTS evidence",
        "DROP TABLE IF EXISTS controls",
        "DROP TABLE IF EXISTS users",
        "DROP TABLE IF EXISTS integration_runs",
        "DROP TABLE IF EXISTS frameworks",
        ]
    )

    for statement in statements:
        bind.exec_driver_sql(statement)
