from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app import repository
from app.auth import require_role
from app.schemas import (
    AuditCreate,
    AuditFindingCreate,
    AuditFindingOut,
    AuditFindingUpdate,
    AuditOut,
    AuditPeriodCreate,
    AuditPeriodOut,
)


router = APIRouter(tags=["audits"])


@router.get("/api/audit-periods", response_model=list[AuditPeriodOut])
def get_audit_periods(
    current_user: dict[str, Any] = Depends(require_role("viewer")),
) -> list[dict]:
    return repository.list_audit_periods()


@router.post("/api/audit-periods", response_model=AuditPeriodOut, status_code=201)
def post_audit_period(
    payload: AuditPeriodCreate,
    current_user: dict[str, Any] = Depends(require_role("compliance_manager")),
) -> dict:
    try:
        period = repository.create_audit_period(payload, created_by=current_user["id"])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    repository.log_audit_event(
        actor_id=current_user["id"],
        action="create",
        object_type="audit_period",
        object_id=period["id"],
        previous_state=None,
        new_state=period,
    )
    return period


@router.get("/api/audits", response_model=list[AuditOut])
def get_audits(
    current_user: dict[str, Any] = Depends(require_role("viewer")),
) -> list[dict]:
    return repository.list_audits()


@router.post("/api/audits", response_model=AuditOut, status_code=201)
def post_audit(
    payload: AuditCreate,
    current_user: dict[str, Any] = Depends(require_role("compliance_manager")),
) -> dict:
    try:
        audit = repository.create_audit(payload, created_by=current_user["id"])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    repository.log_audit_event(
        actor_id=current_user["id"],
        action="create",
        object_type="audit",
        object_id=audit["id"],
        previous_state=None,
        new_state=audit,
    )
    return audit


@router.get("/api/audits/{audit_id}/workspace")
def get_audit_workspace(
    audit_id: int,
    current_user: dict[str, Any] = Depends(require_role("viewer")),
) -> dict:
    workspace = repository.get_audit_workspace(audit_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found")
    return workspace


@router.get("/api/audits/{audit_id}/coverage")
def get_audit_coverage(
    audit_id: int,
    current_user: dict[str, Any] = Depends(require_role("viewer")),
) -> dict:
    workspace = repository.get_audit_workspace(audit_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found")

    period = workspace.get("period") or {}
    return {
        "audit_id": audit_id,
        "period_start": period.get("period_start"),
        "period_end": period.get("period_end"),
        "controls": [
            {
                "control_id": item["control_id"],
                "control_ref": item["control_ref"],
                "evidence_status": item["evidence_status"],
                "gap": item["evidence_status"] != "locked",
            }
            for item in workspace["controls"]
        ],
    }


@router.post("/api/audits/{audit_id}/findings", response_model=AuditFindingOut, status_code=201)
def post_audit_finding(
    audit_id: int,
    payload: AuditFindingCreate,
    current_user: dict[str, Any] = Depends(require_role("security_reviewer")),
) -> dict:
    if repository.get_audit(audit_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found")
    finding = repository.create_audit_finding(audit_id, payload)
    repository.log_audit_event(
        actor_id=current_user["id"],
        action="create",
        object_type="audit_finding",
        object_id=finding["id"],
        previous_state=None,
        new_state=finding,
    )
    return finding


@router.patch("/api/audits/{audit_id}/findings/{finding_id}", response_model=AuditFindingOut)
def patch_audit_finding(
    audit_id: int,
    finding_id: int,
    payload: AuditFindingUpdate,
    current_user: dict[str, Any] = Depends(require_role("security_reviewer")),
) -> dict:
    existing = repository.get_audit_finding(audit_id, finding_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")
    updated = repository.update_audit_finding(audit_id, finding_id, payload)
    repository.log_audit_event(
        actor_id=current_user["id"],
        action="update",
        object_type="audit_finding",
        object_id=finding_id,
        previous_state=existing,
        new_state=updated,
    )
    return updated


@router.get("/api/audits/{audit_id}/export")
def export_audit(
    audit_id: int,
    current_user: dict[str, Any] = Depends(require_role("compliance_manager")),
) -> FileResponse:
    try:
        path = repository.export_audit_packet(audit_id)
    except ValueError as exc:
        if "not found" in str(exc).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    repository.log_audit_event(
        actor_id=current_user["id"],
        action="export",
        object_type="audit",
        object_id=audit_id,
        previous_state=None,
        new_state={"export_path": str(path)},
    )
    return FileResponse(path, filename=path.name, media_type="application/zip")
