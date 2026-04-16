from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db_schema import BOOTSTRAP_SQL

from .session import DATABASE_URL, SessionLocal, engine, get_db_session


class _LegacyConnection:
    def __init__(self, conn: Any) -> None:
        self._conn = conn

    def __enter__(self) -> "_LegacyConnection":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> bool:
        try:
            if exc_type is None:
                self._conn.commit()
            else:
                self._conn.rollback()
        finally:
            self._conn.close()
        return False

    def __getattr__(self, name: str) -> Any:
        return getattr(self._conn, name)


def get_connection() -> _LegacyConnection:
    """Legacy raw SQL connection used by existing services during migration."""

    conn = engine.raw_connection()
    if DATABASE_URL.startswith("sqlite"):
        conn.driver_connection.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
    return _LegacyConnection(conn)


def init_db() -> None:
    """Initialize the legacy bootstrap schema for local/dev startup."""

    if DATABASE_URL.startswith("sqlite:///"):
        db_path = Path(DATABASE_URL.replace("sqlite:///", "", 1))
        db_path.parent.mkdir(parents=True, exist_ok=True)

    with engine.connect() as conn:
        bootstrap_sql = BOOTSTRAP_SQL
        if DATABASE_URL.startswith("sqlite"):
            bootstrap_sql = bootstrap_sql.replace(
                "id SERIAL PRIMARY KEY",
                "id INTEGER PRIMARY KEY AUTOINCREMENT",
            )
        for statement in bootstrap_sql.split(";"):
            if statement.strip():
                conn.execute(text(statement))
        conn.commit()


__all__ = [
    "DATABASE_URL",
    "Session",
    "SessionLocal",
    "engine",
    "get_connection",
    "get_db_session",
    "init_db",
]
