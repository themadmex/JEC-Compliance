from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app import repository
from app.auth import require_role
from app.services import integrations


router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("/status")
def get_integration_status(
    current_user: dict[str, Any] = Depends(require_role("viewer")),
) -> list[dict]:
    return [s.__dict__ for s in integrations.get_statuses()]


@router.get("/runs")
def get_integration_runs(
    limit: int = 25,
    current_user: dict[str, Any] = Depends(require_role("viewer")),
) -> list[dict]:
    return repository.list_integration_runs(limit=limit)


@router.post("/sync")
def post_sync(
    control_id: int | None = None,
    current_user: dict[str, Any] = Depends(require_role("compliance_manager")),
) -> dict:
    return integrations.sync_all(control_id=control_id)
