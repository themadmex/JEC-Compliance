from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.db import get_connection
from app.schemas import TaskCreate


def list_tasks(owner_id: int | None = None, status: str | None = None, task_type: str | None = None) -> list[dict[str, Any]]:
    query = """
        SELECT id, type, source_object_type, source_object_id, title, description,
               owner_id, due_date, status, priority, created_at, completed_at
        FROM tasks
        WHERE 1 = 1
    """
    params: list[Any] = []
    if owner_id is not None:
        query += " AND owner_id = ?"
        params.append(owner_id)
    if status is not None:
        query += " AND status = ?"
        params.append(status)
    if task_type is not None:
        query += " AND type = ?"
        params.append(task_type)
    query += " ORDER BY COALESCE(due_date, created_at) ASC, id ASC"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def create_task(payload: TaskCreate) -> dict[str, Any]:
    completed_at = datetime.now(timezone.utc).isoformat() if payload.status == "completed" else None
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO tasks (
                type, source_object_type, source_object_id, title, description,
                owner_id, due_date, status, priority, completed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.type,
                payload.source_object_type,
                payload.source_object_id,
                payload.title,
                payload.description,
                payload.owner_id,
                payload.due_date.isoformat() if payload.due_date else None,
                payload.status,
                payload.priority,
                completed_at,
            ),
        )
        row = conn.execute(
            """
            SELECT id, type, source_object_type, source_object_id, title, description,
                   owner_id, due_date, status, priority, created_at, completed_at
            FROM tasks
            WHERE id = ?
            """,
            (int(cursor.lastrowid),),
        ).fetchone()
        return dict(row)


def get_task(task_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, type, source_object_type, source_object_id, title, description,
                   owner_id, due_date, status, priority, created_at, completed_at
            FROM tasks
            WHERE id = ?
            """,
            (task_id,),
        ).fetchone()
        return dict(row) if row else None


def update_task_status(task_id: int, new_status: str) -> dict[str, Any] | None:
    existing = get_task(task_id)
    if existing is None:
        return None
    completed_at = datetime.now(timezone.utc).isoformat() if new_status == "completed" else None
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE tasks
            SET status = ?, completed_at = ?
            WHERE id = ?
            """,
            (new_status, completed_at, task_id),
        )
    return get_task(task_id)
