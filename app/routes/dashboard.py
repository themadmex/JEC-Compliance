from __future__ import annotations

from fastapi import APIRouter

from app import repository
from app.schemas import GapItem, Phase1Overview, ReadinessSummary
from app.services import integrations


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/readiness", response_model=ReadinessSummary)
def get_readiness() -> dict:
    return repository.get_readiness_summary()


@router.get("/gaps", response_model=list[GapItem])
def get_gaps() -> list[dict]:
    return repository.get_gap_report()


@router.get("/overview", response_model=Phase1Overview)
def get_overview() -> dict:
    vendors_attention = 0 if integrations.get_statuses()[0].configured else 1
    return repository.get_phase1_overview(vendors_attention=vendors_attention)
