from __future__ import annotations

from typing import Any
from app.db import get_connection


def upsert_user(profile: dict[str, Any]) -> dict[str, Any]:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO users (oid, email, name)
            VALUES (?, ?, ?)
            ON CONFLICT(oid) DO UPDATE SET
                email = excluded.email,
                name = excluded.name,
                last_login_at = datetime('now')
            """,
            (profile["oid"], profile["email"], profile["name"]),
        )
        row = conn.execute(
            "SELECT id, oid, email, name, role FROM users WHERE oid = ?",
            (profile["oid"],),
        ).fetchone()
        return dict(row)


def list_auditor_users() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, email, name, role, scoped_token, token_expires_at
            FROM users
            WHERE role = 'auditor'
            ORDER BY name, email
            """
        ).fetchall()
    return [dict(row) for row in rows]
