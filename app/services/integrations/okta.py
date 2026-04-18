from __future__ import annotations

import logging
import os
from typing import Any

import requests
from sqlalchemy.orm import Session

from app.services.integrations.base import IntegrationBase, IntegrationRunResult

logger = logging.getLogger(__name__)

_TEST_MODE = os.environ.get("TEST_MODE", "false").lower() == "true"

_FIXTURE_USERS: list[dict[str, Any]] = [
    {
        "id": "okta-001",
        "profile": {"email": "alice@example.com", "displayName": "Alice Example"},
        "status": "ACTIVE",
        "recentDeprovisioned": False,
    }
]


def _is_configured() -> bool:
    return bool(os.environ.get("OKTA_DOMAIN") and os.environ.get("OKTA_API_TOKEN"))


def _headers() -> dict[str, str]:
    token = os.environ["OKTA_API_TOKEN"]
    return {"Authorization": f"SSWS {token}", "Accept": "application/json"}


def _fetch_users() -> list[dict[str, Any]]:
    if _TEST_MODE:
        return _FIXTURE_USERS

    domain = os.environ["OKTA_DOMAIN"].rstrip("/")
    url = f"https://{domain}/api/v1/users?limit=200&filter=status+eq+%22ACTIVE%22"
    users: list[dict[str, Any]] = []
    while url:
        resp = requests.get(url, headers=_headers(), timeout=30)
        resp.raise_for_status()
        users.extend(resp.json())
        links = resp.links
        url = links.get("next", {}).get("url", "")
    return users


class OktaIntegration(IntegrationBase):
    name = "okta"

    def health_check(self) -> bool:
        if not _is_configured():
            return False
        if _TEST_MODE:
            return True
        try:
            domain = os.environ["OKTA_DOMAIN"].rstrip("/")
            resp = requests.get(
                f"https://{domain}/api/v1/users?limit=1",
                headers=_headers(),
                timeout=10,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def sync(self, db: Session) -> IntegrationRunResult:
        if not _is_configured():
            run = self._start_run(db)
            result = IntegrationRunResult(
                integration_name=self.name,
                status="failed",
                error_message="OKTA_DOMAIN or OKTA_API_TOKEN not configured",
            )
            self._finish_run(db, run, result)
            db.commit()
            return result

        run = self._start_run(db)
        try:
            users = _fetch_users()
            snapshots = [
                {
                    "resource_type": "user",
                    "resource_id": u.get("id", ""),
                    "data": {
                        "email": u.get("profile", {}).get("email"),
                        "display_name": u.get("profile", {}).get("displayName"),
                        "status": u.get("status"),
                    },
                }
                for u in users
            ]
            count = self._write_snapshots(db, run, snapshots)
            result = IntegrationRunResult(
                integration_name=self.name, status="success", records_synced=count
            )
        except Exception as exc:
            logger.exception("Okta sync failed")
            result = IntegrationRunResult(
                integration_name=self.name, status="failed", error_message=str(exc)
            )

        self._finish_run(db, run, result)
        db.commit()
        return result
