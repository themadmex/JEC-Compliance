from __future__ import annotations

from fastapi import APIRouter

from app.jobs import evidence_monitor


router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/run-evidence-check")
def run_evidence_check() -> dict:
    return evidence_monitor.run()

