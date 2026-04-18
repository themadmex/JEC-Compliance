from __future__ import annotations

import logging
import os
from typing import Any

from sqlalchemy.orm import Session

from app.services.integrations.base import IntegrationBase, IntegrationRunResult

logger = logging.getLogger(__name__)

_TEST_MODE = os.environ.get("TEST_MODE", "false").lower() == "true"

_FIXTURE_USERS: list[dict[str, Any]] = [
    {
        "id": "fixture-user-1",
        "primaryEmail": "alice@example.com",
        "name": {"fullName": "Alice Example"},
        "suspended": False,
        "isAdmin": True,
        "isEnforcedIn2Sv": True,
    },
    {
        "id": "fixture-user-2",
        "primaryEmail": "bob@example.com",
        "name": {"fullName": "Bob Example"},
        "suspended": False,
        "isAdmin": False,
        "isEnforcedIn2Sv": False,
    },
]


def _fetch_users() -> list[dict[str, Any]]:
    if _TEST_MODE:
        return _FIXTURE_USERS

    key_path = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    domain = os.environ["GOOGLE_WORKSPACE_DOMAIN"]

    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    scopes = ["https://www.googleapis.com/auth/admin.directory.user.readonly"]
    creds = service_account.Credentials.from_service_account_file(key_path, scopes=scopes)
    delegated = creds.with_subject(os.environ["GOOGLE_ADMIN_EMAIL"])
    service = build("admin", "directory_v1", credentials=delegated)

    users: list[dict[str, Any]] = []
    page_token = None
    while True:
        result = (
            service.users()
            .list(customer="my_customer", domain=domain, pageToken=page_token, maxResults=500)
            .execute()
        )
        users.extend(result.get("users", []))
        page_token = result.get("nextPageToken")
        if not page_token:
            break

    return users


class GoogleWorkspaceIntegration(IntegrationBase):
    name = "google_workspace"

    def health_check(self) -> bool:
        if _TEST_MODE:
            return True
        try:
            _fetch_users()
            return True
        except Exception:
            return False

    def sync(self, db: Session) -> IntegrationRunResult:
        run = self._start_run(db)
        try:
            users = _fetch_users()
            snapshots = [
                {
                    "resource_type": "user",
                    "resource_id": u.get("id", u.get("primaryEmail", "")),
                    "data": {
                        "email": u.get("primaryEmail"),
                        "display_name": u.get("name", {}).get("fullName"),
                        "suspended": u.get("suspended", False),
                        "is_admin": u.get("isAdmin", False),
                        "mfa_enforced": u.get("isEnforcedIn2Sv", False),
                    },
                }
                for u in users
            ]
            count = self._write_snapshots(db, run, snapshots)
            result = IntegrationRunResult(
                integration_name=self.name, status="success", records_synced=count
            )
        except Exception as exc:
            logger.exception("Google Workspace sync failed")
            result = IntegrationRunResult(
                integration_name=self.name, status="failed", error_message=str(exc)
            )

        self._finish_run(db, run, result)
        db.commit()
        return result
