from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.db import SessionLocal
from app.models.integrations import IntegrationRun
from app.services.integrations.aws import AWSIntegration
from app.services.integrations.base import IntegrationBase, IntegrationRunResult
from app.services.integrations.github import GitHubIntegration
from app.services.integrations.google_workspace import GoogleWorkspaceIntegration
from app.services.integrations.okta import OktaIntegration
from app.services.integrations.sharepoint import SharePointIntegration

ALL_PROVIDERS: list[IntegrationBase] = [
    SharePointIntegration(),
    GoogleWorkspaceIntegration(),
    GitHubIntegration(),
    AWSIntegration(),
    OktaIntegration(),
]


@dataclass
class IntegrationStatus:
    source: str
    configured: bool
    detail: str


def get_statuses() -> list[IntegrationStatus]:
    statuses: list[IntegrationStatus] = []
    for provider in ALL_PROVIDERS:
        try:
            configured = provider.health_check()
        except Exception as exc:
            statuses.append(
                IntegrationStatus(
                    source=provider.name,
                    configured=False,
                    detail=str(exc),
                )
            )
            continue

        statuses.append(
            IntegrationStatus(
                source=provider.name,
                configured=configured,
                detail="Connected" if configured else "Not configured or unreachable",
            )
        )
    return statuses


def sync_all(control_id: int | None = None) -> dict[str, Any]:
    started_at = datetime.now(timezone.utc)
    results: list[dict[str, Any]] = []
    db = SessionLocal()
    try:
        for provider in ALL_PROVIDERS:
            try:
                if not provider.health_check():
                    run = IntegrationRun(
                        source=provider.name,
                        integration_name=provider.name,
                        started_at=datetime.now(timezone.utc),
                        finished_at=datetime.now(timezone.utc),
                        status="skipped",
                        details="Provider is not configured or reachable",
                        records_synced=0,
                    )
                    db.add(run)
                    db.commit()
                    results.append(
                        {
                            "source": provider.name,
                            "status": "skipped",
                            "records_synced": 0,
                            "reason": "Provider is not configured or reachable",
                        }
                    )
                    continue

                result = provider.sync(db)
                results.append(
                    {
                        "source": result.integration_name,
                        "status": result.status,
                        "records_synced": result.records_synced,
                        "error_message": result.error_message,
                    }
                )
            except Exception as exc:
                db.rollback()
                results.append(
                    {
                        "source": provider.name,
                        "status": "failed",
                        "records_synced": 0,
                        "error_message": str(exc),
                    }
                )
    finally:
        db.close()

    if any(result["status"] == "failed" for result in results):
        status = "partial"
    elif results and all(result["status"] == "skipped" for result in results):
        status = "skipped"
    else:
        status = "ok"

    response: dict[str, Any] = {
        "status": status,
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "started_at": started_at.isoformat(),
        "results": results,
    }
    if control_id is not None:
        response["control_id"] = control_id
    return response


__all__ = [
    "ALL_PROVIDERS",
    "AWSIntegration",
    "GitHubIntegration",
    "GoogleWorkspaceIntegration",
    "IntegrationStatus",
    "IntegrationBase",
    "IntegrationRunResult",
    "OktaIntegration",
    "SharePointIntegration",
    "get_statuses",
    "sync_all",
]
