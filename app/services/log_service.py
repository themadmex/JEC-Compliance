from __future__ import annotations

import json
from typing import Any
from app.db import get_connection


def log_audit_event(
    actor_id: int,
    action: str,
    object_type: str,
    object_id: int,
    previous_state: dict[str, Any] | None,
    new_state: dict[str, Any] | None,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO audit_log (
                actor_id, action, object_type, object_id, previous_state, new_state
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                actor_id,
                action,
                object_type,
                object_id,
                json.dumps(previous_state, default=str) if previous_state is not None else None,
                json.dumps(new_state, default=str) if new_state is not None else None,
            ),
        )
