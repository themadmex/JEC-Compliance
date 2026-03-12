from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app import repository
from app.schemas import EvidenceCreate
from app.services import sharepoint

router = APIRouter(prefix="/sharepoint", tags=["sharepoint"])


class AttachRequest(BaseModel):
    control_id: int
    item_id: str
    name: str
    notes: str | None = None


@router.get("/status")
def sp_status() -> dict[str, Any]:
    """Check SharePoint connectivity."""
    return sharepoint.check_connection()


@router.get("/browse")
def browse(folder: str = "") -> list[dict[str, Any]]:
    """List files in the SharePoint Documents library."""
    if not sharepoint.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SharePoint not configured — set SHAREPOINT_SITE_URL in .env",
        )
    return sharepoint.browse_files(folder_path=folder)


@router.post("/attach", status_code=201)
def attach(payload: AttachRequest) -> dict[str, Any]:
    """Attach an existing SharePoint file as evidence for a control."""
    if not sharepoint.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SharePoint not configured",
        )
    meta = sharepoint.get_file_metadata(payload.item_id)
    evidence = repository.create_evidence(
        EvidenceCreate(
            control_id=payload.control_id,
            name=payload.name,
            source="sharepoint",
            artifact_path=meta["web_url"],
            collected_at=datetime.now(timezone.utc),
            status="accepted",
            notes=payload.notes,
        )
    )
    return evidence


@router.get("/lists")
def list_sp_lists() -> list[dict[str, Any]]:
    """Return all visible SharePoint Lists on the site."""
    if not sharepoint.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SharePoint not configured",
        )
    return sharepoint.get_lists()


@router.post("/provision-folders")
def provision_folders() -> dict[str, Any]:
    """Create the compliance folder tree on SharePoint (idempotent)."""
    if not sharepoint.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SharePoint not configured",
        )
    return sharepoint.provision_folder_structure()


@router.get("/lists/{list_name}/items")
def list_items(list_name: str) -> list[dict[str, Any]]:
    """Return all items from a SharePoint List."""
    if not sharepoint.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SharePoint not configured",
        )
    return sharepoint.get_list_items(list_name)
