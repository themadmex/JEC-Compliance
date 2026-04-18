from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db_schema import BOOTSTRAP_SQL

from .session import DATABASE_URL, SessionLocal, engine, get_db_session

_IS_SQLITE = DATABASE_URL.startswith("sqlite")


def _translate_sql(sql: str, params: Any) -> tuple[str, Any]:
    """Translate SQLite SQL dialect to PostgreSQL dialect."""
    # INSERT OR IGNORE → INSERT ... ON CONFLICT DO NOTHING
    was_ignore = bool(re.search(r"\bINSERT\s+OR\s+IGNORE\b", sql, re.IGNORECASE))
    sql = re.sub(r"\bINSERT\s+OR\s+IGNORE\b", "INSERT", sql, flags=re.IGNORECASE)
    if was_ignore:
        sql = sql.rstrip().rstrip(";") + " ON CONFLICT DO NOTHING"
    # Placeholder style
    if isinstance(params, dict):
        sql = re.sub(r":(\w+)", r"%(\1)s", sql)
    else:
        sql = sql.replace("?", "%s")
    # SQLite-specific date function
    sql = re.sub(r"datetime\('now'\)", "NOW()", sql, flags=re.IGNORECASE)
    return sql, params


class _CompatCursor:
    """Wraps a psycopg2 cursor to present a uniform interface."""

    def __init__(self, cursor: Any) -> None:
        self._cursor = cursor

    def fetchone(self) -> Any:
        return self._cursor.fetchone()

    def fetchall(self) -> Any:
        return self._cursor.fetchall()

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount

    @property
    def lastrowid(self) -> int | None:
        # psycopg2 does not expose lastrowid; use RETURNING id in INSERT statements.
        return None


class _LegacyConnection:
    def __init__(self, conn: Any) -> None:
        self._conn = conn

    def __enter__(self) -> "_LegacyConnection":
        return self

    def __exit__(self, exc_type: Any, _exc: Any, _traceback: Any) -> bool:
        try:
            if exc_type is None:
                self._conn.commit()
            else:
                self._conn.rollback()
        finally:
            self._conn.close()
        return False

    def execute(self, sql: str, params: Any = None) -> Any:
        if _IS_SQLITE:
            raw = self._conn.driver_connection
            if params is None:
                return raw.execute(sql)
            return raw.execute(sql, params)
        # PostgreSQL path: translate dialect and use cursor
        from psycopg2.extras import RealDictCursor  # type: ignore[import]

        sql, params = _translate_sql(sql, params)
        cursor = self._conn.cursor(cursor_factory=RealDictCursor)
        if params is None:
            cursor.execute(sql)
        else:
            cursor.execute(sql, params)
        return _CompatCursor(cursor)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._conn, name)


def get_table_columns(conn: _LegacyConnection, table_name: str) -> set[str]:
    """Return the set of column names for a table (cross-dialect)."""
    if _IS_SQLITE:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    else:
        rows = conn.execute(
            "SELECT column_name AS name FROM information_schema.columns WHERE table_name = ?",
            (table_name,),
        ).fetchall()
    return {row["name"] for row in rows}


def get_connection() -> _LegacyConnection:
    """Legacy raw SQL connection with cross-dialect compatibility."""
    conn = engine.raw_connection()
    if _IS_SQLITE:
        conn.driver_connection.row_factory = sqlite3.Row
        conn.driver_connection.execute("PRAGMA foreign_keys = ON;")
    return _LegacyConnection(conn)


def init_db() -> None:
    """Initialize the legacy bootstrap schema for local/dev startup."""
    if _IS_SQLITE:
        db_path = Path(DATABASE_URL.replace("sqlite:///", "", 1))
        db_path.parent.mkdir(parents=True, exist_ok=True)

    with engine.connect() as conn:
        bootstrap_sql = BOOTSTRAP_SQL
        if _IS_SQLITE:
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
    "get_table_columns",
    "init_db",
]
