from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.auth import require_role
from app.jobs import evidence_monitor


router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/run-evidence-check")
def run_evidence_check(
    current_user: dict[str, Any] = Depends(require_role("compliance_manager")),
) -> dict:
    return evidence_monitor.run()
