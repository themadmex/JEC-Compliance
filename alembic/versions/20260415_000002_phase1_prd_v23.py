"""Phase 1 PRD v2.3 schema additions.

Revision ID: 20260415_000002
Revises: 20260313_000001
Create Date: 2026-04-15 12:00:00
"""
from __future__ import annotations

from alembic import op


revision = "20260415_000002"
down_revision = "20260313_000001"
branch_labels = None
depends_on = None


def _table_names() -> set[str]:
    bind = op.get_bind()
    rows = bind.exec_driver_sql(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    return {row[0] for row in rows}


def _columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    return {row[1] for row in bind.exec_driver_sql(f"PRAGMA table_info({table_name})")}


def _add_column_if_missing(table_name: str, column_name: str, ddl: str) -> None:
    if column_name not in _columns(table_name):
        op.get_bind().exec_driver_sql(f"ALTER TABLE {table_name} ADD COLUMN {ddl}")


def _create_index_if_missing(name: str, table_name: str, columns: str, unique: bool = False) -> None:
    uniqueness = "UNIQUE " if unique else ""
    op.get_bind().exec_driver_sql(
        f"CREATE {uniqueness}INDEX IF NOT EXISTS {name} ON {table_name} ({columns})"
    )


def upgrade() -> None:
    bind = op.get_bind()
    tables = _table_names()

    if "frameworks" in tables:
        _add_column_if_missing("frameworks", "description", "description TEXT")
        _add_column_if_missing("frameworks", "created_at", "created_at TEXT")
        bind.exec_driver_sql("UPDATE frameworks SET created_at = datetime('now') WHERE created_at IS NULL")

    if "controls" in tables:
        for column_name, ddl in [
            ("control_code", "control_code TEXT"),
            ("category", "category TEXT"),
            ("owner_user_id", "owner_user_id INTEGER REFERENCES users(id)"),
            ("frequency", "frequency TEXT DEFAULT 'manual'"),
            ("is_automated", "is_automated INTEGER NOT NULL DEFAULT 0"),
            ("type1_status", "type1_status TEXT NOT NULL DEFAULT 'not_started'"),
            ("type2_status", "type2_status TEXT NOT NULL DEFAULT 'not_started'"),
            ("next_review_date", "next_review_date TEXT"),
            ("evidence_requirements", "evidence_requirements TEXT"),
            ("created_at", "created_at TEXT"),
            ("updated_at", "updated_at TEXT"),
        ]:
            _add_column_if_missing("controls", column_name, ddl)
        bind.exec_driver_sql("UPDATE controls SET created_at = datetime('now') WHERE created_at IS NULL")
        bind.exec_driver_sql("UPDATE controls SET control_code = control_id WHERE control_code IS NULL")
        bind.exec_driver_sql(
            """
            UPDATE controls
            SET type1_status = CASE WHEN type1_ready = 1 THEN 'implemented' ELSE 'not_started' END
            WHERE type1_status IS NULL OR type1_status = 'not_started'
            """
        )
        bind.exec_driver_sql(
            """
            UPDATE controls
            SET type2_status = CASE WHEN type2_ready = 1 THEN 'operating' ELSE 'not_started' END
            WHERE type2_status IS NULL OR type2_status = 'not_started'
            """
        )
        _create_index_if_missing("uq_controls_control_code", "controls", "control_code", unique=True)

    if "users" in tables:
        for column_name, ddl in [
            ("entra_oid", "entra_oid TEXT"),
            ("display_name", "display_name TEXT"),
            ("is_active", "is_active INTEGER NOT NULL DEFAULT 1"),
            ("last_login", "last_login TEXT"),
        ]:
            _add_column_if_missing("users", column_name, ddl)
        bind.exec_driver_sql("UPDATE users SET entra_oid = oid WHERE entra_oid IS NULL")
        bind.exec_driver_sql("UPDATE users SET display_name = name WHERE display_name IS NULL")
        bind.exec_driver_sql("UPDATE users SET last_login = last_login_at WHERE last_login IS NULL")
        _create_index_if_missing("uq_users_entra_oid", "users", "entra_oid", unique=True)

    if "evidence" in tables:
        for column_name, ddl in [
            ("title", "title TEXT"),
            ("description", "description TEXT"),
            ("source_type", "source_type TEXT"),
            ("uploaded_by", "uploaded_by INTEGER REFERENCES users(id)"),
            ("reviewed_by", "reviewed_by INTEGER REFERENCES users(id)"),
            ("rejection_reason", "rejection_reason TEXT"),
            ("valid_from", "valid_from TEXT"),
            ("valid_to", "valid_to TEXT"),
            ("sharepoint_url", "sharepoint_url TEXT"),
            ("sharepoint_item_id", "sharepoint_item_id TEXT"),
            ("local_path", "local_path TEXT"),
            ("file_name", "file_name TEXT"),
            ("file_size_bytes", "file_size_bytes INTEGER"),
            ("mime_type", "mime_type TEXT"),
            ("locked_by", "locked_by INTEGER REFERENCES users(id)"),
            ("created_at", "created_at TEXT"),
            ("updated_at", "updated_at TEXT"),
        ]:
            _add_column_if_missing("evidence", column_name, ddl)
        bind.exec_driver_sql("UPDATE evidence SET created_at = datetime('now') WHERE created_at IS NULL")
        bind.exec_driver_sql("UPDATE evidence SET title = name WHERE title IS NULL")
        bind.exec_driver_sql("UPDATE evidence SET source_type = source WHERE source_type IS NULL")
        bind.exec_driver_sql("UPDATE evidence SET uploaded_by = submitter_id WHERE uploaded_by IS NULL")
        bind.exec_driver_sql("UPDATE evidence SET reviewed_by = approver_id WHERE reviewed_by IS NULL")
        bind.exec_driver_sql("UPDATE evidence SET rejection_reason = rejected_reason WHERE rejection_reason IS NULL")
        bind.exec_driver_sql("UPDATE evidence SET valid_from = COALESCE(period_start, collected_at) WHERE valid_from IS NULL")
        bind.exec_driver_sql("UPDATE evidence SET valid_to = period_end WHERE valid_to IS NULL")
        bind.exec_driver_sql("UPDATE evidence SET sharepoint_item_id = sharepoint_id WHERE sharepoint_item_id IS NULL")
        bind.exec_driver_sql("UPDATE evidence SET local_path = artifact_path WHERE local_path IS NULL")
        bind.exec_driver_sql("UPDATE evidence SET file_name = name WHERE file_name IS NULL")

    if "control_checks" in tables:
        for column_name, ddl in [
            ("check_name", "check_name TEXT"),
            ("status", "status TEXT"),
            ("result_summary", "result_summary TEXT"),
            ("result_detail", "result_detail TEXT"),
            ("run_at", "run_at TEXT"),
            ("duration_ms", "duration_ms INTEGER"),
            ("triggered_by", "triggered_by TEXT DEFAULT 'scheduler'"),
            ("created_task_id", "created_task_id INTEGER REFERENCES tasks(id)"),
        ]:
            _add_column_if_missing("control_checks", column_name, ddl)
        bind.exec_driver_sql("UPDATE control_checks SET check_name = 'legacy_check' WHERE check_name IS NULL")
        bind.exec_driver_sql("UPDATE control_checks SET status = result WHERE status IS NULL")
        bind.exec_driver_sql("UPDATE control_checks SET result_summary = details WHERE result_summary IS NULL")
        bind.exec_driver_sql("UPDATE control_checks SET result_detail = details WHERE result_detail IS NULL")
        bind.exec_driver_sql("UPDATE control_checks SET run_at = checked_at WHERE run_at IS NULL")

    if "integration_runs" in tables:
        for column_name, ddl in [
            ("integration_name", "integration_name TEXT"),
            ("error_message", "error_message TEXT"),
            ("records_synced", "records_synced INTEGER NOT NULL DEFAULT 0"),
        ]:
            _add_column_if_missing("integration_runs", column_name, ddl)
        bind.exec_driver_sql("UPDATE integration_runs SET integration_name = source WHERE integration_name IS NULL")

    if "audit_periods" in tables:
        for column_name, ddl in [
            ("report_type", "report_type TEXT"),
            ("observation_start", "observation_start TEXT"),
            ("observation_end", "observation_end TEXT"),
            ("point_in_time_date", "point_in_time_date TEXT"),
            ("created_by", "created_by INTEGER REFERENCES users(id)"),
        ]:
            _add_column_if_missing("audit_periods", column_name, ddl)
        bind.exec_driver_sql("UPDATE audit_periods SET report_type = type WHERE report_type IS NULL")
        bind.exec_driver_sql("UPDATE audit_periods SET observation_start = period_start WHERE observation_start IS NULL")
        bind.exec_driver_sql("UPDATE audit_periods SET observation_end = period_end WHERE observation_end IS NULL")

    if "audits" in tables:
        for column_name, ddl in [
            ("period_id", "period_id INTEGER REFERENCES audit_periods(id)"),
            ("audit_firm", "audit_firm TEXT"),
            ("early_access_date", "early_access_date TEXT"),
            ("fieldwork_start", "fieldwork_start TEXT"),
            ("fieldwork_end", "fieldwork_end TEXT"),
            ("report_date", "report_date TEXT"),
            ("lead_auditor_email", "lead_auditor_email TEXT"),
        ]:
            _add_column_if_missing("audits", column_name, ddl)
        bind.exec_driver_sql("UPDATE audits SET period_id = audit_period_id WHERE period_id IS NULL")
        bind.exec_driver_sql("UPDATE audits SET audit_firm = firm_name WHERE audit_firm IS NULL")

    if "audit_requests" in tables:
        for column_name, ddl in [
            ("created_by", "created_by INTEGER REFERENCES users(id)"),
            ("request_type", "request_type TEXT DEFAULT 'evidence_request'"),
            ("sample_size", "sample_size INTEGER"),
        ]:
            _add_column_if_missing("audit_requests", column_name, ddl)
        bind.exec_driver_sql("UPDATE audit_requests SET created_by = requested_by WHERE created_by IS NULL")

    if "audit_request_evidence" in tables:
        for column_name, ddl in [
            ("attached_by", "attached_by INTEGER REFERENCES users(id)"),
            ("attached_at", "attached_at TEXT"),
        ]:
            _add_column_if_missing("audit_request_evidence", column_name, ddl)
        bind.exec_driver_sql(
            "UPDATE audit_request_evidence SET attached_at = datetime('now') WHERE attached_at IS NULL"
        )

    new_table_statements = [
        """
        CREATE TABLE IF NOT EXISTS check_evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            check_id INTEGER NOT NULL REFERENCES control_checks(id) ON DELETE CASCADE,
            evidence_id INTEGER NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(check_id, evidence_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS audit_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            audit_id INTEGER NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id),
            assigned_at TEXT NOT NULL DEFAULT (datetime('now')),
            assigned_by INTEGER REFERENCES users(id),
            access_expires_at TEXT,
            UNIQUE(audit_id, user_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS audit_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            audit_id INTEGER NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
            request_id INTEGER REFERENCES audit_requests(id) ON DELETE CASCADE,
            evidence_id INTEGER REFERENCES evidence(id),
            parent_id INTEGER REFERENCES audit_comments(id),
            author_id INTEGER NOT NULL REFERENCES users(id),
            body TEXT NOT NULL,
            is_internal INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS readiness_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            audit_period_id INTEGER NOT NULL REFERENCES audit_periods(id) ON DELETE CASCADE,
            report_type TEXT NOT NULL,
            calculated_at TEXT NOT NULL DEFAULT (datetime('now')),
            calculated_by INTEGER REFERENCES users(id),
            overall_score NUMERIC(5,2),
            controls_ready INTEGER NOT NULL DEFAULT 0,
            controls_partial INTEGER NOT NULL DEFAULT 0,
            controls_not_ready INTEGER NOT NULL DEFAULT 0,
            controls_not_applicable INTEGER NOT NULL DEFAULT 0,
            summary_json TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS readiness_gaps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_id INTEGER NOT NULL REFERENCES readiness_snapshots(id) ON DELETE CASCADE,
            control_id INTEGER NOT NULL REFERENCES controls(id),
            gap_type TEXT NOT NULL,
            gap_start TEXT,
            gap_end TEXT,
            severity TEXT NOT NULL,
            detail TEXT NOT NULL
        )
        """,
    ]
    for statement in new_table_statements:
        bind.exec_driver_sql(statement)


def downgrade() -> None:
    bind = op.get_bind()
    for statement in [
        "DROP TABLE IF EXISTS readiness_gaps",
        "DROP TABLE IF EXISTS readiness_snapshots",
        "DROP TABLE IF EXISTS audit_comments",
        "DROP TABLE IF EXISTS audit_users",
        "DROP TABLE IF EXISTS check_evidence",
        "DROP INDEX IF EXISTS uq_users_entra_oid",
        "DROP INDEX IF EXISTS uq_controls_control_code",
    ]:
        bind.exec_driver_sql(statement)
