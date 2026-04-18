from __future__ import annotations

import hashlib
import magic
from datetime import datetime, date, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app import repository
from app.auth import require_role
from app.schemas import EvidenceCreate, EvidenceOut, EvidenceRejectRequest, EvidenceStatus
from app.services import sharepoint

router = APIRouter(prefix="/evidence", tags=["evidence"])
ARTIFACTS_DIR = Path("artifacts")
LOCKED_DIR = ARTIFACTS_DIR / "locked"


@router.get("", response_model=list[EvidenceOut])
def get_evidence(
    control_id: int | None = None,
    current_user: dict[str, Any] = Depends(require_role("viewer")),
) -> list[dict]:
    if current_user["role"] == "auditor":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Use audit-scoped evidence endpoints")
    return repository.list_evidence(control_id=control_id)


@router.post("", response_model=EvidenceOut, status_code=201)
def post_evidence(
    payload: EvidenceCreate,
    current_user: dict[str, Any] = Depends(require_role("contributor")),
) -> dict:
    if current_user["role"] == "auditor":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Auditors cannot create evidence directly")
    return repository.create_evidence(
        payload.model_copy(
            update={
                "uploaded_by": payload.uploaded_by or current_user["id"],
                "status": payload.status,
            }
        )
    )


def _load_evidence_bytes(evidence: dict[str, Any]) -> bytes:
    sharepoint_item_id = evidence.get("sharepoint_item_id")
    if sharepoint_item_id and sharepoint.is_configured():
        sharepoint.get_file_metadata(sharepoint_item_id)
        return sharepoint.download_file(sharepoint_item_id)

    artifact_path = evidence.get("local_path")
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
    title: str = Form(...),
    source_type: str = Form(default="manual"),
    valid_from: date = Form(...),
    valid_to: date | None = Form(default=None),
    description: str | None = Form(default=None),
    file: UploadFile = File(...),
    current_user: dict[str, Any] = Depends(require_role("contributor")),
) -> dict:
    if current_user["role"] == "auditor":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Auditors cannot upload evidence directly")
    # 1. Enforce 50MB limit
    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_ENTITY_TOO_LARGE,
            detail="File size exceeds 50MB limit",
        )

    # 2. Validate extension
    filename = file.filename or "evidence.bin"
    extension = filename.split(".")[-1].lower() if "." in filename else ""
    allowlist = {"pdf", "docx", "xlsx", "png", "jpg", "jpeg", "txt", "csv", "zip"}
    if extension not in allowlist:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File extension '.{extension}' not in allowlist",
        )

    # 3. Validate MIME type with magic
    mime_type = magic.from_buffer(content, mime=True)
    # Basic check: doesn't have to be perfect but should be consistent
    if extension == "pdf" and mime_type != "application/pdf":
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="MIME type mismatch for PDF")

    sha256_hash = hashlib.sha256(content).hexdigest()
    content_type = mime_type or file.content_type or "application/octet-stream"
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
        title=title,
        source_type=source_type,
        local_path=artifact_path,
        valid_from=datetime.combine(valid_from, datetime.min.time(), tzinfo=timezone.utc),
        valid_to=datetime.combine(valid_to, datetime.min.time(), tzinfo=timezone.utc) if valid_to else None,
        status="submitted",
        description=description,
        uploaded_by=current_user["id"],
        sha256_hash=sha256_hash,
        sharepoint_item_id=sharepoint_id,
        file_name=filename,
        file_size_bytes=len(content),
        mime_type=content_type,
    )
    repository.log_audit_event(
        actor_id=current_user["id"],
        action="evidence.upload",
        object_type="evidence",
        object_id=0,  # Will be updated by repository on create if we had better logging integration
        previous_state=None,
        new_state=payload.model_dump(mode="json"),
    )
    return repository.create_evidence(payload)


@router.patch(
    "/{evidence_id}/accept",
    response_model=EvidenceOut,
)
def accept_evidence(
    evidence_id: int,
    current_user: dict[str, Any] = Depends(require_role("compliance_manager")),
) -> dict:
    previous = repository.get_evidence(evidence_id)
    if previous is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    try:
        evidence = repository.approve_evidence(evidence_id, reviewer_id=current_user["id"])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    repository.log_audit_event(
        actor_id=current_user["id"],
        action="evidence.accept",
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
        evidence = repository.reject_evidence(evidence_id, reviewer_id=current_user["id"], rejected_reason=payload.rejected_reason)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    repository.log_audit_event(
        actor_id=current_user["id"],
        action="evidence.reject",
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

    if sharepoint.is_configured() and previous.get("sharepoint_item_id"):
        # PRD Section 7.4.4: Copy to locked folder in SharePoint
        # We use audit_period_id as the grouping folder
        audit_id = previous.get("audit_period_id") or 0
        new_sp_url = sharepoint.copy_to_locked_folder(
            previous["sharepoint_item_id"],
            audit_id=audit_id,
            evidence_id=evidence_id
        )
        # In a real impl, we'd update sharepoint_url here.
    else:
        LOCKED_DIR.mkdir(parents=True, exist_ok=True)
        locked_path = LOCKED_DIR / previous["sha256_hash"]
        if not locked_path.exists():
            locked_path.write_bytes(live_bytes)

    locked_at = datetime.now(timezone.utc).isoformat()
    try:
        evidence = repository.lock_evidence(evidence_id, locked_by=current_user["id"], locked_at=locked_at)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    repository.log_audit_event(
        actor_id=current_user["id"],
        action="evidence.lock",
        object_type="evidence",
        object_id=evidence_id,
        previous_state=previous,
        new_state=evidence,
    )
    return evidence
