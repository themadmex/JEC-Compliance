from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app import repository
from app.auth import get_current_user, require_role
from app.schemas import EvidenceCreate, EvidenceOut, EvidenceRejectRequest
from app.services import sharepoint

router = APIRouter(prefix="/evidence", tags=["evidence"])
ARTIFACTS_DIR = Path("artifacts")
LOCKED_DIR = ARTIFACTS_DIR / "locked"


@router.get("", response_model=list[EvidenceOut])
def get_evidence(
    control_id: int | None = None,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[dict]:
    return repository.list_evidence(control_id=control_id)


@router.post("", response_model=EvidenceOut, status_code=201)
def post_evidence(
    payload: EvidenceCreate,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict:
    return repository.create_evidence(
        payload.model_copy(
            update={
                "submitter_id": payload.submitter_id or current_user["id"],
                "status": payload.status if payload.status != "accepted" else "submitted",
            }
        )
    )


def _load_evidence_bytes(evidence: dict[str, Any]) -> bytes:
    if evidence.get("sharepoint_id") and sharepoint.is_configured():
        sharepoint.get_file_metadata(evidence["sharepoint_id"])
        return sharepoint.download_file(evidence["sharepoint_id"])

    artifact_path = evidence.get("artifact_path")
    if not artifact_path:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Evidence has no artifact path")

    path = Path(artifact_path)
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Evidence artifact file not found for locking",
        )
    return path.read_bytes()


@router.post("/upload", response_model=EvidenceOut, status_code=201)
async def upload_evidence(
    control_id: int = Form(...),
    name: str = Form(...),
    source: str = Form(...),
    notes: str | None = Form(default=None),
    file: UploadFile = File(...),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict:
    content = await file.read()
    sha256_hash = hashlib.sha256(content).hexdigest()
    filename = file.filename or "evidence.bin"
    content_type = file.content_type or "application/octet-stream"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_name = f"{timestamp}_{filename}"
    sharepoint_id: str | None = None

    if sharepoint.is_configured():
        sp_meta = sharepoint.upload_file(safe_name, content, content_type)
        artifact_path = sp_meta["web_url"]
        sharepoint_id = sp_meta.get("sharepoint_id")
    else:
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        destination = ARTIFACTS_DIR / safe_name
        destination.write_bytes(content)
        artifact_path = str(destination)

    payload = EvidenceCreate(
        control_id=control_id,
        name=name,
        source=source,
        artifact_path=artifact_path,
        collected_at=datetime.now(timezone.utc),
        status="submitted",
        notes=notes,
        submitter_id=current_user["id"],
        sha256_hash=sha256_hash,
        sharepoint_id=sharepoint_id,
    )
    return repository.create_evidence(payload)


@router.patch(
    "/{evidence_id}/approve",
    response_model=EvidenceOut,
)
def approve_evidence(
    evidence_id: int,
    current_user: dict[str, Any] = Depends(require_role("compliance_manager")),
) -> dict:
    previous = repository.get_evidence(evidence_id)
    if previous is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    try:
        evidence = repository.approve_evidence(evidence_id, approver_id=current_user["id"])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    repository.log_audit_event(
        actor_id=current_user["id"],
        action="approve",
        object_type="evidence",
        object_id=evidence_id,
        previous_state=previous,
        new_state=evidence,
    )
    return evidence


@router.patch(
    "/{evidence_id}/reject",
    response_model=EvidenceOut,
)
def reject_evidence(
    evidence_id: int,
    payload: EvidenceRejectRequest,
    current_user: dict[str, Any] = Depends(require_role("compliance_manager")),
) -> dict:
    previous = repository.get_evidence(evidence_id)
    if previous is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    try:
        evidence = repository.reject_evidence(evidence_id, rejected_reason=payload.rejected_reason)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    repository.log_audit_event(
        actor_id=current_user["id"],
        action="reject",
        object_type="evidence",
        object_id=evidence_id,
        previous_state=previous,
        new_state=evidence,
    )
    return evidence


@router.patch(
    "/{evidence_id}/lock",
    response_model=EvidenceOut,
)
def lock_evidence(
    evidence_id: int,
    current_user: dict[str, Any] = Depends(require_role("compliance_manager")),
) -> dict:
    previous = repository.get_evidence(evidence_id)
    if previous is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    if not previous.get("sha256_hash"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Evidence missing hash and cannot be locked",
        )

    try:
        live_bytes = _load_evidence_bytes(previous)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Evidence source file is unavailable for locking",
        ) from exc

    live_hash = hashlib.sha256(live_bytes).hexdigest()
    if live_hash != previous["sha256_hash"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Hash mismatch at lock",
                "stored_hash": previous["sha256_hash"],
                "live_hash": live_hash,
            },
        )

    LOCKED_DIR.mkdir(parents=True, exist_ok=True)
    locked_path = LOCKED_DIR / previous["sha256_hash"]
    if not locked_path.exists():
        locked_path.write_bytes(live_bytes)

    locked_at = datetime.now(timezone.utc).isoformat()
    try:
        evidence = repository.lock_evidence(evidence_id, locked_at=locked_at)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    repository.log_audit_event(
        actor_id=current_user["id"],
        action="lock",
        object_type="evidence",
        object_id=evidence_id,
        previous_state=previous,
        new_state=evidence,
    )
    return evidence
