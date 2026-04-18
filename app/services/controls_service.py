from __future__ import annotations

from typing import Any

from app.db import get_connection
from app.schemas import ControlCreate


DEFAULT_FRAMEWORK_NAME = "SOC 2"
DEFAULT_FRAMEWORK_VERSION = "2017 TSC"


def _ensure_framework() -> int:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO frameworks (name, version)
            VALUES (?, ?)
            """,
            (DEFAULT_FRAMEWORK_NAME, DEFAULT_FRAMEWORK_VERSION),
        )
        row = conn.execute(
            """
            SELECT id
            FROM frameworks
            WHERE name = ? AND version = ?
            """,
            (DEFAULT_FRAMEWORK_NAME, DEFAULT_FRAMEWORK_VERSION),
        ).fetchone()
        return int(row["id"])


def list_controls() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, control_id, title, description, owner, implementation_status,
                   type1_ready, type2_ready, last_tested_at, next_review_at
            FROM controls
            ORDER BY control_id
            """
        ).fetchall()
        return [dict(row) for row in rows]


def get_control(control_db_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, control_id, title, description, owner, implementation_status,
                   type1_ready, type2_ready, last_tested_at, next_review_at
            FROM controls
            WHERE id = ?
            """,
            (control_db_id,),
        ).fetchone()
        return dict(row) if row else None


def create_control(payload: ControlCreate) -> dict[str, Any]:
    framework_id = _ensure_framework()
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO controls (
                framework_id, control_id, title, description, owner,
                implementation_status, type1_ready, type2_ready,
                last_tested_at, next_review_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
            """,
            (
                framework_id,
                payload.control_id,
                payload.title,
                payload.description,
                payload.owner,
                payload.implementation_status,
                int(payload.type1_ready),
                int(payload.type2_ready),
                payload.last_tested_at.isoformat() if payload.last_tested_at else None,
                payload.next_review_at.isoformat() if payload.next_review_at else None,
            ),
        )
        new_id = int(cursor.fetchone()["id"])
        row = conn.execute(
            """
            SELECT id, control_id, title, description, owner, implementation_status,
                   type1_ready, type2_ready, last_tested_at, next_review_at
            FROM controls
            WHERE id = ?
            """,
            (new_id,),
        ).fetchone()
        return dict(row)


def update_control_status(control_db_id: int, status: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE controls
            SET implementation_status = ?
            WHERE id = ?
            """,
            (status, control_db_id),
        )
        row = conn.execute(
            """
            SELECT id, control_id, title, description, owner, implementation_status,
                   type1_ready, type2_ready, last_tested_at, next_review_at
            FROM controls
            WHERE id = ?
            """,
            (control_db_id,),
        ).fetchone()
        return dict(row) if row else None
