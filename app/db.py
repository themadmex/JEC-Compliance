from __future__ import annotations

import sqlite3
from pathlib import Path


DB_DIR = Path("data")
DB_PATH = DB_DIR / "jec_soc2.db"


def get_connection() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {str(row["name"]) for row in rows}


def _ensure_column(
    conn: sqlite3.Connection,
    table_name: str,
    column_name: str,
    definition: str,
) -> None:
    if column_name in _table_columns(conn, table_name):
        return
    conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS frameworks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                version TEXT NOT NULL,
                UNIQUE(name, version)
            );

            CREATE TABLE IF NOT EXISTS controls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            );

            CREATE TABLE IF NOT EXISTS evidence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                control_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                source TEXT NOT NULL,
                artifact_path TEXT NOT NULL,
                collected_at TEXT NOT NULL,
                period_start TEXT,
                period_end TEXT,
                status TEXT NOT NULL DEFAULT 'accepted',
                notes TEXT,
                FOREIGN KEY(control_id) REFERENCES controls(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS control_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                control_id INTEGER NOT NULL,
                checked_at TEXT NOT NULL,
                result TEXT NOT NULL,
                details TEXT NOT NULL,
                FOREIGN KEY(control_id) REFERENCES controls(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS integration_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT NOT NULL,
                status TEXT NOT NULL,
                details TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                oid TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL,
                name TEXT,
                role TEXT NOT NULL DEFAULT 'viewer',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                last_login_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor_id INTEGER,
                action TEXT NOT NULL,
                object_type TEXT NOT NULL,
                object_id INTEGER NOT NULL,
                previous_state TEXT,
                new_state TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY(actor_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS audit_periods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                period_start TEXT NOT NULL,
                period_end TEXT NOT NULL,
                type TEXT NOT NULL,
                created_by INTEGER,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY(created_by) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                source_object_type TEXT NOT NULL,
                source_object_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                owner_id INTEGER NOT NULL,
                due_date TEXT,
                status TEXT NOT NULL DEFAULT 'open',
                priority TEXT NOT NULL DEFAULT 'medium',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                completed_at TEXT,
                FOREIGN KEY(owner_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS audits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                audit_period_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                firm_name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                scope_notes TEXT,
                created_by INTEGER,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                closed_at TEXT,
                FOREIGN KEY(created_by) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS audit_controls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                audit_id INTEGER NOT NULL,
                control_id INTEGER NOT NULL,
                evidence_status TEXT NOT NULL DEFAULT 'missing',
                assigned_to INTEGER,
                notes TEXT,
                FOREIGN KEY(audit_id) REFERENCES audits(id) ON DELETE CASCADE,
                FOREIGN KEY(control_id) REFERENCES controls(id) ON DELETE CASCADE,
                FOREIGN KEY(assigned_to) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS audit_findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                audit_id INTEGER NOT NULL,
                control_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                severity TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                owner_id INTEGER NOT NULL,
                due_date TEXT,
                closed_at TEXT,
                remediation_notes TEXT,
                FOREIGN KEY(audit_id) REFERENCES audits(id) ON DELETE CASCADE,
                FOREIGN KEY(control_id) REFERENCES controls(id) ON DELETE CASCADE,
                FOREIGN KEY(owner_id) REFERENCES users(id)
            );

            CREATE INDEX IF NOT EXISTS idx_audit_log_object
                ON audit_log(object_type, object_id);
            CREATE INDEX IF NOT EXISTS idx_audit_log_actor
                ON audit_log(actor_id);
            CREATE INDEX IF NOT EXISTS idx_audit_log_time
                ON audit_log(created_at);

            CREATE TRIGGER IF NOT EXISTS audit_log_no_update
            BEFORE UPDATE ON audit_log
            BEGIN
                SELECT RAISE(ABORT, 'audit_log rows are immutable');
            END;

            CREATE TRIGGER IF NOT EXISTS audit_log_no_delete
            BEFORE DELETE ON audit_log
            BEGIN
                SELECT RAISE(ABORT, 'audit_log rows are immutable');
            END;
            """
        )

        _ensure_column(conn, "evidence", "submitter_id", "INTEGER")
        _ensure_column(conn, "evidence", "approver_id", "INTEGER")
        _ensure_column(conn, "evidence", "approved_at", "TEXT")
        _ensure_column(conn, "evidence", "rejected_reason", "TEXT")
        _ensure_column(conn, "evidence", "locked_at", "TEXT")
        _ensure_column(conn, "evidence", "sha256_hash", "TEXT")
        _ensure_column(conn, "evidence", "sharepoint_id", "TEXT")
        _ensure_column(conn, "evidence", "audit_period_id", "INTEGER")
        _ensure_column(conn, "evidence", "collection_due_date", "TEXT")
