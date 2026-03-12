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
            """
        )
