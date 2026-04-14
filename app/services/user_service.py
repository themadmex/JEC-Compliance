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
