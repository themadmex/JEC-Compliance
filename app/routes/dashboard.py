from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app import repository
from app.auth import require_role
from app.schemas import GapItem, Phase1Overview, ReadinessSummary
from app.services import integrations


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/readiness", response_model=ReadinessSummary)
def get_readiness(
    current_user: dict[str, Any] = Depends(require_role("viewer")),
) -> dict:
    return repository.get_readiness_summary()


@router.get("/gaps", response_model=list[GapItem])
def get_gaps(
    current_user: dict[str, Any] = Depends(require_role("viewer")),
) -> list[dict]:
    return repository.get_gap_report()


@router.get("/overview", response_model=Phase1Overview)
def get_overview(
    current_user: dict[str, Any] = Depends(require_role("viewer")),
) -> dict:
    vendors_attention = 0 if integrations.get_statuses()[0].configured else 1
    return repository.get_phase1_overview(vendors_attention=vendors_attention)


@router.get("/summary")
def get_summary(
    current_user: dict[str, Any] = Depends(require_role("viewer")),
) -> dict:
    return repository.get_dashboard_summary()
