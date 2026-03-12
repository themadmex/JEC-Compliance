from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app import repository
from app.schemas import EvidenceCreate
from app.services import sharepoint


@dataclass
class IntegrationStatus:
    source: str
    configured: bool
    detail: str


def get_statuses() -> list[IntegrationStatus]:
    sp_check = sharepoint.check_connection()
    return [
        IntegrationStatus(
            source="sharepoint",
            configured=sp_check["ok"],
            detail=(
                sp_check.get("site_id", "Connected")
                if sp_check["ok"]
                else sp_check.get("reason", "Set SHAREPOINT_SITE_URL in .env")
            ),
        )
    ]


def _sync_sharepoint(now: datetime) -> dict[str, Any]:
    if not sharepoint.is_configured():
        return {"source": "sharepoint", "status": "skipped", "reason": "SHAREPOINT_SITE_URL not set"}

    try:
        files = sharepoint.browse_files()
    except Exception as exc:
        return {"source": "sharepoint", "status": "error", "reason": str(exc)}

    latest = files[0] if files else {}
    return {
        "source": "sharepoint",
        "status": "ok",
        "files_found": len(files),
        "latest_item_name": latest.get("name"),
        "checked_at": now.isoformat(),
    }


def sync_all(control_id: int | None = None) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    chosen_control_id = control_id or repository.get_default_control_id()
    if chosen_control_id is None:
        return {"status": "error", "message": "No controls exist yet. Create a control first."}

    started_at = datetime.now(timezone.utc)
    details = _sync_sharepoint(now)
    status = details.get("status", "ok")
    finished_at = datetime.now(timezone.utc)

    repository.log_integration_run(
        source="sharepoint",
        started_at=started_at.isoformat(),
        finished_at=finished_at.isoformat(),
        status=status,
        details=json.dumps(details),
    )

    if details.get("status") == "ok":
        repository.create_evidence(
            EvidenceCreate(
                control_id=chosen_control_id,
                name="sharepoint integration check",
                source="sharepoint",
                artifact_path=f"sharepoint://{details.get('latest_item_name', 'root')}",
                collected_at=finished_at,
                status="accepted",
                notes=json.dumps(details),
            )
        )

    return {"status": "ok", "synced_at": now.isoformat(), "results": [details]}
