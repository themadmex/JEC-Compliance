from __future__ import annotations

from fastapi import APIRouter

from app import repository
from app.services import integrations


router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("/status")
def get_integration_status() -> list[dict]:
    return [s.__dict__ for s in integrations.get_statuses()]


@router.get("/runs")
def get_integration_runs(limit: int = 25) -> list[dict]:
    return repository.list_integration_runs(limit=limit)


@router.post("/sync")
def post_sync(control_id: int | None = None) -> dict:
    return integrations.sync_all(control_id=control_id)

