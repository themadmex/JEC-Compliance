from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app import repository
from app.auth import require_role
from app.schemas import (
    AuditCommentCreate,
    AuditControlUpdate,
    AuditCreate,
    AuditFindingCreate,
    AuditFindingOut,
    AuditFindingUpdate,
    AuditPeriodCreate,
    AuditPeriodOut,
    AuditRequestCreate,
    AuditRequestEvidenceCreate,
    AuditRequestUpdate,
    AuditUpdate,
    AuditorAssignmentCreate,
)


router = APIRouter(prefix="/api/v1", tags=["audits"])


def _require_audit_scope(audit_id: int, user: dict[str, Any]) -> None:
    if user["role"] == "auditor" and not repository.auditor_has_scope(audit_id, user["id"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Audit scope denied")


def _can_access_audit(audit_id: int, user: dict[str, Any]) -> None:
    if user["role"] == "auditor":
        _require_audit_scope(audit_id, user)


@router.get("/audit-periods", response_model=list[AuditPeriodOut])
def get_audit_periods(
    current_user: dict[str, Any] = Depends(require_role("viewer")),
) -> list[dict]:
    return repository.list_audit_periods()


@router.post("/audit-periods", response_model=AuditPeriodOut, status_code=201)
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
        action="audit_period.create",
        object_type="audit_period",
        object_id=period["id"],
        previous_state=None,
        new_state=period,
    )
    return period


@router.get("/audits")
def get_audits(
    current_user: dict[str, Any] = Depends(require_role("viewer")),
) -> list[dict]:
    if current_user["role"] == "auditor":
        return repository.list_audits_for_auditor(current_user["id"])
    return repository.list_audits()


@router.post("/audits", status_code=201)
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
        action="audit.create",
        object_type="audit",
        object_id=audit["id"],
        previous_state=None,
        new_state=audit,
    )
    return audit


@router.get("/audits/{audit_id}")
def get_audit(
    audit_id: int,
    current_user: dict[str, Any] = Depends(require_role("viewer")),
) -> dict:
    _can_access_audit(audit_id, current_user)
    workspace = repository.get_audit_workspace(audit_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found")
    return workspace


@router.patch("/audits/{audit_id}")
def patch_audit(
    audit_id: int,
    payload: AuditUpdate,
    current_user: dict[str, Any] = Depends(require_role("compliance_manager")),
) -> dict:
    previous = repository.get_audit(audit_id)
    if previous is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found")
    updated = repository.update_audit(audit_id, payload)
    repository.log_audit_event(
        actor_id=current_user["id"],
        action="audit.status_change" if payload.status else "audit.update",
        object_type="audit",
        object_id=audit_id,
        previous_state=previous,
        new_state=updated,
    )
    if payload.status == "completed":
        repository.log_audit_event(
            actor_id=current_user["id"],
            action="auditor.access_expired",
            object_type="audit",
            object_id=audit_id,
            previous_state=None,
            new_state={"audit_id": audit_id},
        )
    return updated


@router.patch("/audits/{audit_id}/controls/{control_id}")
def patch_audit_control(
    audit_id: int,
    control_id: int,
    payload: AuditControlUpdate,
    current_user: dict[str, Any] = Depends(require_role("compliance_manager")),
) -> dict:
    updated = repository.update_audit_control(audit_id, control_id, payload)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit control not found")
    return updated


@router.get("/auditors")
def get_auditor_users(
    current_user: dict[str, Any] = Depends(require_role("compliance_manager")),
) -> list[dict]:
    return repository.list_auditor_users()


@router.get("/audits/{audit_id}/auditors")
def get_audit_auditors(
    audit_id: int,
    current_user: dict[str, Any] = Depends(require_role("compliance_manager")),
) -> list[dict]:
    if repository.get_audit(audit_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found")
    return repository.list_audit_auditors(audit_id)


@router.post("/audits/{audit_id}/auditors", status_code=201)
def post_auditor(
    audit_id: int,
    payload: AuditorAssignmentCreate,
    current_user: dict[str, Any] = Depends(require_role("compliance_manager")),
) -> dict:
    try:
        assignment = repository.assign_auditor(audit_id, payload, assigned_by=current_user["id"])
    except TypeError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    repository.log_audit_event(
        actor_id=current_user["id"],
        action="auditor.assigned",
        object_type="audit",
        object_id=audit_id,
        previous_state=None,
        new_state=assignment,
    )
    return assignment


@router.delete("/audits/{audit_id}/auditors/{user_id}", status_code=204)
def delete_auditor(
    audit_id: int,
    user_id: int,
    current_user: dict[str, Any] = Depends(require_role("compliance_manager")),
) -> None:
    removed = repository.remove_auditor(audit_id, user_id)
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Auditor assignment not found")
    repository.log_audit_event(
        actor_id=current_user["id"],
        action="auditor.revoked",
        object_type="audit",
        object_id=audit_id,
        previous_state={"user_id": user_id},
        new_state=None,
    )


@router.get("/audits/{audit_id}/preview-as-auditor")
def preview_as_auditor(
    audit_id: int,
    current_user: dict[str, Any] = Depends(require_role("compliance_manager")),
) -> dict:
    portal = repository.get_auditor_portal(audit_id, include_internal=False)
    if portal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found")
    return portal


@router.post("/audits/{audit_id}/export")
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
        action="export.generated",
        object_type="audit",
        object_id=audit_id,
        previous_state=None,
        new_state={"export_path": str(path)},
    )
    return FileResponse(path, filename=path.name, media_type="application/zip")


@router.get("/audits/{audit_id}/readiness/type1")
def get_type1_readiness(
    audit_id: int,
    current_user: dict[str, Any] = Depends(require_role("viewer")),
) -> dict:
    _can_access_audit(audit_id, current_user)
    return repository.calculate_readiness(audit_id, "type1")


@router.get("/audits/{audit_id}/readiness/type2")
def get_type2_readiness(
    audit_id: int,
    current_user: dict[str, Any] = Depends(require_role("viewer")),
) -> dict:
    _can_access_audit(audit_id, current_user)
    return repository.calculate_readiness(audit_id, "type2")


@router.get("/audits/{audit_id}/requests")
def get_audit_requests(
    audit_id: int,
    current_user: dict[str, Any] = Depends(require_role("viewer")),
) -> list[dict]:
    _can_access_audit(audit_id, current_user)
    return repository.list_audit_requests(audit_id, include_internal=current_user["role"] != "auditor")


@router.post("/audits/{audit_id}/requests", status_code=201)
def post_audit_request(
    audit_id: int,
    payload: AuditRequestCreate,
    current_user: dict[str, Any] = Depends(require_role("auditor")),
) -> dict:
    _can_access_audit(audit_id, current_user)
    try:
        item = repository.create_request(audit_id, payload, user_id=current_user["id"])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    repository.log_audit_event(
        actor_id=current_user["id"],
        action="request.create",
        object_type="audit_request",
        object_id=item["id"],
        previous_state=None,
        new_state=item,
    )
    return item


@router.get("/requests/{request_id}")
def get_request(
    request_id: int,
    current_user: dict[str, Any] = Depends(require_role("viewer")),
) -> dict:
    include_internal = current_user["role"] != "auditor"
    item = repository.get_request(request_id, include_internal=include_internal)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    _can_access_audit(item["audit_id"], current_user)
    return item


@router.patch("/requests/{request_id}")
def patch_request(
    request_id: int,
    payload: AuditRequestUpdate,
    current_user: dict[str, Any] = Depends(require_role("auditor")),
) -> dict:
    existing = repository.get_request(request_id, include_internal=True)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    _can_access_audit(existing["audit_id"], current_user)
    if payload.assigned_to is not None and current_user["role"] == "auditor":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Auditors cannot assign requests")
    updated = repository.update_request(request_id, payload)
    repository.log_audit_event(
        actor_id=current_user["id"],
        action="request.status_change",
        object_type="audit_request",
        object_id=request_id,
        previous_state=existing,
        new_state=updated,
    )
    return updated


@router.post("/requests/{request_id}/evidence")
def post_request_evidence(
    request_id: int,
    payload: AuditRequestEvidenceCreate,
    current_user: dict[str, Any] = Depends(require_role("contributor")),
) -> dict:
    request = repository.get_request(request_id, include_internal=True)
    if request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    _can_access_audit(request["audit_id"], current_user)
    try:
        item = repository.attach_request_evidence(request_id, payload, user_id=current_user["id"])
    except ValueError as exc:
        message = str(exc)
        if "not found" in message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc
    return item


@router.post("/requests/{request_id}/comments", status_code=201)
def post_request_comment(
    request_id: int,
    payload: AuditCommentCreate,
    current_user: dict[str, Any] = Depends(require_role("auditor")),
) -> dict:
    request = repository.get_request(request_id, include_internal=True)
    if request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    _can_access_audit(request["audit_id"], current_user)
    if payload.is_internal and current_user["role"] not in {"compliance_manager", "security_reviewer", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only internal users can create internal comments")
    try:
        comment = repository.add_request_comment(request_id, payload, user_id=current_user["id"])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    repository.log_audit_event(
        actor_id=current_user["id"],
        action="request.comment",
        object_type="audit_request",
        object_id=request_id,
        previous_state=None,
        new_state=comment,
    )
    return comment


@router.post("/audits/{audit_id}/findings", response_model=AuditFindingOut, status_code=201)
def post_audit_finding(
    audit_id: int,
    payload: AuditFindingCreate,
    current_user: dict[str, Any] = Depends(require_role("security_reviewer")),
) -> dict:
    try:
        finding = repository.create_audit_finding(audit_id, payload, created_by=current_user["id"])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    repository.log_audit_event(
        actor_id=current_user["id"],
        action="audit_finding.create",
        object_type="audit_finding",
        object_id=finding["id"],
        previous_state=None,
        new_state=finding,
    )
    return finding


@router.patch("/audits/{audit_id}/findings/{finding_id}", response_model=AuditFindingOut)
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
        action="audit_finding.update",
        object_type="audit_finding",
        object_id=finding_id,
        previous_state=existing,
        new_state=updated,
    )
    return updated
