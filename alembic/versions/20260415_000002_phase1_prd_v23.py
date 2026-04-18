"""Phase 1 PRD v2.3 schema additions.

Revision ID: 20260415_000002
Revises: 20260313_000001
Create Date: 2026-04-15 12:00:00
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import inspect


revision = "20260415_000002"
down_revision = "20260313_000001"
branch_labels = None
depends_on = None


def _table_names() -> set[str]:
    bind = op.get_bind()
    return set(inspect(bind).get_table_names())


def _columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    return {column["name"] for column in inspect(bind).get_columns(table_name)}


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
    dialect = bind.dialect.name
    id_type = "SERIAL PRIMARY KEY" if dialect == "postgresql" else "INTEGER PRIMARY KEY AUTOINCREMENT"
    now_default = "now()" if dialect == "postgresql" else "datetime('now')"
    now_text = "now()::text" if dialect == "postgresql" else "datetime('now')"
    tables = _table_names()

    if "frameworks" in tables:
        _add_column_if_missing("frameworks", "description", "description TEXT")
        _add_column_if_missing("frameworks", "created_at", "created_at TEXT")
        bind.exec_driver_sql(f"UPDATE frameworks SET created_at = {now_default} WHERE created_at IS NULL")

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
        bind.exec_driver_sql(f"UPDATE controls SET created_at = {now_default} WHERE created_at IS NULL")
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
        bind.exec_driver_sql(f"UPDATE evidence SET created_at = {now_default} WHERE created_at IS NULL")
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

    if "control_checks" in tables and "tasks" not in tables:
        bind.exec_driver_sql(
            f"""
            CREATE TABLE IF NOT EXISTS tasks (
                id {id_type},
                type TEXT,
                source_object_type TEXT,
                source_object_id INTEGER,
                control_id INTEGER REFERENCES controls(id),
                check_id INTEGER,
                title TEXT NOT NULL,
                description TEXT,
                owner_id INTEGER REFERENCES users(id),
                assigned_to INTEGER REFERENCES users(id),
                due_date TEXT,
                status TEXT NOT NULL DEFAULT 'open',
                priority TEXT NOT NULL DEFAULT 'medium',
                created_by INTEGER REFERENCES users(id),
                created_at TEXT DEFAULT ({now_default}),
                updated_at TEXT,
                completed_at TEXT,
                resolved_at TEXT
            )
            """
        )
        tables.add("tasks")

    if "control_checks" in tables:
        for column_name, ddl in [
            ("check_name", "check_name TEXT"),
            ("status", "status TEXT"),
            ("result_summary", "result_summary TEXT"),
            ("result_detail", "result_detail TEXT"),
            ("run_at", "run_at TEXT"),
            ("duration_ms", "duration_ms INTEGER"),
            ("triggered_by", "triggered_by TEXT DEFAULT 'scheduler'"),
            ("created_task_id", "created_task_id INTEGER"),
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

    if "integration_snapshots" in tables:
        for column_name, ddl in [
            ("run_id", "run_id INTEGER REFERENCES integration_runs(id)"),
            ("integration_name", "integration_name TEXT"),
            ("resource_type", "resource_type TEXT"),
            ("resource_id", "resource_id TEXT"),
            ("data", "data TEXT"),
            ("captured_at", "captured_at TEXT"),
            (
                "is_service_account_candidate",
                "is_service_account_candidate INTEGER NOT NULL DEFAULT 0",
            ),
            ("service_account_reason", "service_account_reason TEXT"),
        ]:
            _add_column_if_missing("integration_snapshots", column_name, ddl)
        bind.exec_driver_sql(
            "UPDATE integration_snapshots SET integration_name = source WHERE integration_name IS NULL"
        )
        bind.exec_driver_sql(
            "UPDATE integration_snapshots SET resource_type = snapshot_type WHERE resource_type IS NULL"
        )
        bind.exec_driver_sql(
            "UPDATE integration_snapshots SET data = data_json WHERE data IS NULL"
        )

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
            ("notes", "notes TEXT"),
            ("updated_at", "updated_at TEXT"),
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
            f"UPDATE audit_request_evidence SET attached_at = {now_default} WHERE attached_at IS NULL"
        )

    support_table_statements = [
        f"""
        CREATE TABLE IF NOT EXISTS integration_snapshots (
            id {id_type},
            run_id INTEGER REFERENCES integration_runs(id) ON DELETE CASCADE,
            source TEXT,
            snapshot_type TEXT,
            data_json TEXT,
            integration_name TEXT,
            resource_type TEXT,
            resource_id TEXT,
            data TEXT,
            is_service_account_candidate INTEGER NOT NULL DEFAULT 0,
            service_account_reason TEXT,
            collected_at TEXT DEFAULT ({now_default}),
            captured_at TEXT
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS audit_periods (
            id {id_type},
            framework_id INTEGER REFERENCES frameworks(id),
            name TEXT NOT NULL,
            period_start TEXT,
            period_end TEXT,
            type TEXT,
            report_type TEXT,
            observation_start TEXT,
            observation_end TEXT,
            point_in_time_date TEXT,
            created_by INTEGER REFERENCES users(id),
            created_at TEXT DEFAULT ({now_default})
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS tasks (
            id {id_type},
            type TEXT,
            source_object_type TEXT,
            source_object_id INTEGER,
            control_id INTEGER REFERENCES controls(id),
            check_id INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            owner_id INTEGER REFERENCES users(id),
            assigned_to INTEGER REFERENCES users(id),
            due_date TEXT,
            status TEXT NOT NULL DEFAULT 'open',
            priority TEXT NOT NULL DEFAULT 'medium',
            created_by INTEGER REFERENCES users(id),
            created_at TEXT DEFAULT ({now_default}),
            updated_at TEXT,
            completed_at TEXT,
            resolved_at TEXT
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS audits (
            id {id_type},
            audit_period_id INTEGER REFERENCES audit_periods(id),
            period_id INTEGER REFERENCES audit_periods(id),
            type TEXT,
            firm_name TEXT,
            audit_firm TEXT,
            status TEXT NOT NULL DEFAULT 'preparation',
            scope_notes TEXT,
            early_access_date TEXT,
            fieldwork_start TEXT,
            fieldwork_end TEXT,
            report_date TEXT,
            lead_auditor_email TEXT,
            notes TEXT,
            created_by INTEGER REFERENCES users(id),
            created_at TEXT DEFAULT ({now_default}),
            updated_at TEXT,
            closed_at TEXT
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS audit_controls (
            id {id_type},
            audit_id INTEGER NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
            control_id INTEGER NOT NULL REFERENCES controls(id) ON DELETE CASCADE,
            evidence_status TEXT DEFAULT 'missing',
            assigned_to INTEGER REFERENCES users(id),
            notes TEXT,
            in_scope INTEGER NOT NULL DEFAULT 1,
            auditor_notes TEXT,
            UNIQUE(audit_id, control_id)
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS audit_requests (
            id {id_type},
            audit_id INTEGER NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
            control_id INTEGER REFERENCES controls(id),
            title TEXT NOT NULL,
            description TEXT,
            due_date TEXT,
            status TEXT NOT NULL DEFAULT 'open',
            requested_by INTEGER REFERENCES users(id),
            created_by INTEGER REFERENCES users(id),
            assigned_to INTEGER REFERENCES users(id),
            request_type TEXT DEFAULT 'evidence_request',
            sample_size INTEGER,
            created_at TEXT DEFAULT ({now_default}),
            updated_at TEXT
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS audit_request_evidence (
            id {id_type},
            request_id INTEGER NOT NULL REFERENCES audit_requests(id) ON DELETE CASCADE,
            evidence_id INTEGER NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
            attached_by INTEGER REFERENCES users(id),
            created_at TEXT DEFAULT ({now_default}),
            attached_at TEXT,
            UNIQUE(request_id, evidence_id)
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS audit_findings (
            id {id_type},
            audit_id INTEGER NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
            control_id INTEGER REFERENCES controls(id) ON DELETE CASCADE,
            finding_type TEXT,
            severity TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            management_response TEXT,
            status TEXT NOT NULL DEFAULT 'open',
            owner_id INTEGER REFERENCES users(id),
            due_date TEXT,
            closed_at TEXT,
            remediation_notes TEXT,
            created_by INTEGER REFERENCES users(id),
            created_at TEXT DEFAULT ({now_default}),
            updated_at TEXT
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS graph_objects (
            id {id_type},
            object_type TEXT NOT NULL,
            external_key TEXT,
            external_id TEXT,
            title TEXT,
            display_name TEXT,
            subtitle TEXT,
            description TEXT,
            status TEXT,
            owner TEXT,
            metadata_json TEXT DEFAULT '{{}}',
            data TEXT,
            synced_at TEXT,
            created_at TEXT DEFAULT ({now_default}),
            updated_at TEXT
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS graph_links (
            id {id_type},
            left_type TEXT,
            left_id INTEGER,
            right_type TEXT,
            right_id INTEGER,
            link_type TEXT,
            source_id INTEGER REFERENCES graph_objects(id),
            target_id INTEGER REFERENCES graph_objects(id),
            relationship TEXT,
            notes TEXT,
            created_at TEXT DEFAULT ({now_default})
        )
        """,
    ]
    for statement in support_table_statements:
        bind.exec_driver_sql(statement)

    tables = _table_names()

    new_table_statements = [
        f"""
        CREATE TABLE IF NOT EXISTS check_evidence (
            id {id_type},
            check_id INTEGER NOT NULL REFERENCES control_checks(id) ON DELETE CASCADE,
            evidence_id INTEGER NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL DEFAULT ({now_default}),
            UNIQUE(check_id, evidence_id)
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS audit_users (
            id {id_type},
            audit_id INTEGER NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id),
            assigned_at TEXT NOT NULL DEFAULT ({now_default}),
            assigned_by INTEGER REFERENCES users(id),
            access_expires_at TEXT,
            UNIQUE(audit_id, user_id)
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS audit_comments (
            id {id_type},
            audit_id INTEGER NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
            request_id INTEGER REFERENCES audit_requests(id) ON DELETE CASCADE,
            evidence_id INTEGER REFERENCES evidence(id),
            parent_id INTEGER REFERENCES audit_comments(id),
            author_id INTEGER NOT NULL REFERENCES users(id),
            body TEXT NOT NULL,
            is_internal INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT ({now_default}),
            updated_at TEXT
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS readiness_snapshots (
            id {id_type},
            audit_period_id INTEGER NOT NULL REFERENCES audit_periods(id) ON DELETE CASCADE,
            report_type TEXT NOT NULL,
            calculated_at TEXT NOT NULL DEFAULT ({now_default}),
            calculated_by INTEGER REFERENCES users(id),
            overall_score NUMERIC(5,2),
            controls_ready INTEGER NOT NULL DEFAULT 0,
            controls_partial INTEGER NOT NULL DEFAULT 0,
            controls_not_ready INTEGER NOT NULL DEFAULT 0,
            controls_not_applicable INTEGER NOT NULL DEFAULT 0,
            summary_json TEXT NOT NULL
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS readiness_gaps (
            id {id_type},
            snapshot_id INTEGER NOT NULL REFERENCES readiness_snapshots(id) ON DELETE CASCADE,
            control_id INTEGER NOT NULL REFERENCES controls(id),
            gap_type TEXT NOT NULL,
            gap_start TEXT,
            gap_end TEXT,
            severity TEXT NOT NULL,
            detail TEXT NOT NULL
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS evidence_controls (
            id {id_type},
            evidence_id INTEGER NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
            control_id INTEGER NOT NULL REFERENCES controls(id),
            is_primary INTEGER NOT NULL DEFAULT 0,
            mapped_by INTEGER REFERENCES users(id),
            created_at TEXT NOT NULL DEFAULT ({now_default}),
            UNIQUE(evidence_id, control_id)
        )
        """,
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
            control_id INTEGER NOT NULL REFERENCES controls(id),
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
            severity TEXT NOT NULL,
            detail TEXT NOT NULL,
            detected_at TEXT NOT NULL DEFAULT ({now_default}),
            resolved_at TEXT,
            is_active INTEGER NOT NULL DEFAULT 1
        )
        """,
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
            employment_status TEXT,
            risk_flag INTEGER NOT NULL DEFAULT 0,
            decision TEXT,
            decision_by INTEGER REFERENCES users(id),
            decision_at TEXT,
            decision_notes TEXT,
            remediation_task_id INTEGER REFERENCES tasks(id)
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS personnel (
            id {id_type},
            user_id INTEGER REFERENCES users(id),
            email TEXT NOT NULL UNIQUE,
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
            requirement_type TEXT,
            applies_to TEXT,
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
            requirement_id INTEGER NOT NULL REFERENCES personnel_requirements(id),
            status TEXT NOT NULL DEFAULT 'pending',
            completed_at TEXT,
            due_date TEXT,
            evidence_url TEXT,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT ({now_default}),
            updated_at TEXT
        )
        """,
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
            control_id INTEGER NOT NULL REFERENCES controls(id),
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
    for statement in new_table_statements:
        bind.exec_driver_sql(statement)

    bind.exec_driver_sql(
        f"""
        INSERT INTO evidence_controls (evidence_id, control_id, is_primary, created_at)
        SELECT id, control_id, 1, COALESCE(created_at, {now_text})
        FROM evidence
        WHERE control_id IS NOT NULL
        ON CONFLICT (evidence_id, control_id) DO NOTHING
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    for statement in [
        "DROP TABLE IF EXISTS risk_history",
        "DROP TABLE IF EXISTS risk_controls",
        "DROP TABLE IF EXISTS risks",
        "DROP TABLE IF EXISTS personnel_compliance_records",
        "DROP TABLE IF EXISTS personnel_requirements",
        "DROP TABLE IF EXISTS personnel",
        "DROP TABLE IF EXISTS access_review_accounts",
        "DROP TABLE IF EXISTS access_reviews",
        "DROP TABLE IF EXISTS policy_consistency_flags",
        "DROP TABLE IF EXISTS policy_versions",
        "DROP TABLE IF EXISTS policy_controls",
        "DROP TABLE IF EXISTS policies",
        "DROP TABLE IF EXISTS evidence_controls",
        "DROP TABLE IF EXISTS readiness_gaps",
        "DROP TABLE IF EXISTS readiness_snapshots",
        "DROP TABLE IF EXISTS audit_comments",
        "DROP TABLE IF EXISTS audit_users",
        "DROP TABLE IF EXISTS check_evidence",
        "DROP TABLE IF EXISTS graph_links",
        "DROP TABLE IF EXISTS graph_objects",
        "DROP TABLE IF EXISTS audit_findings",
        "DROP TABLE IF EXISTS audit_request_evidence",
        "DROP TABLE IF EXISTS audit_requests",
        "DROP TABLE IF EXISTS audit_controls",
        "DROP TABLE IF EXISTS audits",
        "DROP TABLE IF EXISTS tasks",
        "DROP TABLE IF EXISTS audit_periods",
        "DROP TABLE IF EXISTS integration_snapshots",
        "DROP INDEX IF EXISTS uq_users_entra_oid",
        "DROP INDEX IF EXISTS uq_controls_control_code",
    ]:
        bind.exec_driver_sql(statement)
