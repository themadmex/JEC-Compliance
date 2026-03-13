from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from app import repository
from app.auth import require_role


router = APIRouter(prefix="/api/audit-log", tags=["audit-log"])


@router.get("")
def get_audit_log(
    actor_id: int | None = Query(default=None),
    object_type: str | None = Query(default=None),
    object_id: int | None = Query(default=None),
    current_user: dict[str, Any] = Depends(require_role("admin")),
) -> list[dict]:
    return repository.list_audit_log(
        actor_id=actor_id,
        object_type=object_type,
        object_id=object_id,
    )
