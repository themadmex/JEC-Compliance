from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import require_role
from app.db import get_db_session
from app.services.checks.runner import CheckRunner


router = APIRouter(prefix="/api/v1/checks", tags=["checks"])


def _serialize_result(result) -> dict:
    return {
        "control_code": result.control_code,
        "check_name": result.check_name,
        "status": result.status.value,
        "summary": result.summary,
        "run_at": result.run_at.isoformat(),
    }


@router.get("")
def list_checks(
    current_user: dict[str, Any] = Depends(require_role("viewer")),
    db_session: Session = Depends(get_db_session),
) -> list[dict]:
    runner = CheckRunner(db_session)
    return [
        {
            "control_code": check.control_code,
            "check_name": check.check_name,
            "description": check.description,
        }
        for check in runner.registry.list_checks()
    ]


@router.post("/{control_code}/run")
async def run_check(
    control_code: str,
    current_user: dict[str, Any] = Depends(require_role("compliance_manager")),
    db_session: Session = Depends(get_db_session),
) -> dict:
    result = await CheckRunner(db_session).run_one(control_code, triggered_by="manual")
    if result is None:
        raise HTTPException(status_code=404, detail="No check registered for this control")
    return _serialize_result(result)


@router.post("/run-all")
async def run_all_checks(
    current_user: dict[str, Any] = Depends(require_role("compliance_manager")),
    db_session: Session = Depends(get_db_session),
) -> dict:
    results = await CheckRunner(db_session).run_all(triggered_by="manual")
    return {"count": len(results), "results": [_serialize_result(result) for result in results]}
