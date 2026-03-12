from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile

from app import repository
from app.schemas import EvidenceCreate, EvidenceOut
from app.services import sharepoint

router = APIRouter(prefix="/evidence", tags=["evidence"])
ARTIFACTS_DIR = Path("artifacts")


@router.get("", response_model=list[EvidenceOut])
def get_evidence(control_id: int | None = None) -> list[dict]:
    return repository.list_evidence(control_id=control_id)


@router.post("", response_model=EvidenceOut, status_code=201)
def post_evidence(payload: EvidenceCreate) -> dict:
    return repository.create_evidence(payload)


@router.post("/upload", response_model=EvidenceOut, status_code=201)
async def upload_evidence(
    control_id: int = Form(...),
    name: str = Form(...),
    source: str = Form(...),
    notes: str | None = Form(default=None),
    file: UploadFile = File(...),
) -> dict:
    content = await file.read()
    filename = file.filename or "evidence.bin"
    content_type = file.content_type or "application/octet-stream"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_name = f"{timestamp}_{filename}"

    if sharepoint.is_configured():
        sp_meta = sharepoint.upload_file(safe_name, content, content_type)
        artifact_path = sp_meta["web_url"]
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
        status="accepted",
        notes=notes,
    )
    return repository.create_evidence(payload)
