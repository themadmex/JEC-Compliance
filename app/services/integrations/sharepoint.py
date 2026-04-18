from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass
from typing import Any

import requests
from sqlalchemy.orm import Session

from app.services.integrations.base import IntegrationBase, IntegrationRunResult

logger = logging.getLogger(__name__)

_GRAPH_BASE = "https://graph.microsoft.com/v1.0"
_EVIDENCE_FOLDER = "JEC-Compliance/Evidence"
_LOCKED_FOLDER = "JEC-Compliance/Evidence/Locked"


@dataclass
class SharePointUploadResult:
    item_id: str
    sharepoint_url: str
    sha256_hash: str


def _get_token() -> str:
    tenant = os.environ["AZURE_TENANT_ID"]
    client_id = os.environ["AZURE_CLIENT_ID"]
    client_secret = os.environ["AZURE_CLIENT_SECRET"]
    resp = requests.post(
        f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "https://graph.microsoft.com/.default",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _site_id() -> str:
    site_url = os.environ["SHAREPOINT_SITE_URL"]
    token = _get_token()
    # Extract host and path from site URL
    parts = site_url.replace("https://", "").split("/", 1)
    host = parts[0]
    path = parts[1] if len(parts) > 1 else ""
    resp = requests.get(
        f"{_GRAPH_BASE}/sites/{host}:/{path}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def _drive_id(token: str, site_id: str) -> str:
    resp = requests.get(
        f"{_GRAPH_BASE}/sites/{site_id}/drives",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    resp.raise_for_status()
    drives = resp.json().get("value", [])
    # Use "Documents" drive or first available
    for drive in drives:
        if drive.get("name") == "Documents":
            return drive["id"]
    return drives[0]["id"]


def upload_file(control_code: str, filename: str, content_bytes: bytes) -> SharePointUploadResult:
    sha256 = hashlib.sha256(content_bytes).hexdigest()
    token = _get_token()
    site_id = _site_id()
    drive_id = _drive_id(token, site_id)
    folder_path = f"{_EVIDENCE_FOLDER}/{control_code}"

    # Ensure folder exists by attempting to create it
    requests.post(
        f"{_GRAPH_BASE}/drives/{drive_id}/root:/{folder_path}:/children",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"name": control_code, "folder": {}, "@microsoft.graph.conflictBehavior": "replace"},
        timeout=30,
    )

    upload_url = f"{_GRAPH_BASE}/drives/{drive_id}/root:/{folder_path}/{filename}:/content"
    resp = requests.put(
        upload_url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/octet-stream"},
        data=content_bytes,
        timeout=120,
    )
    resp.raise_for_status()
    item = resp.json()
    web_url = item.get("webUrl", "")
    return SharePointUploadResult(item_id=item["id"], sharepoint_url=web_url, sha256_hash=sha256)


def download_file(item_id: str) -> bytes:
    token = _get_token()
    site_id = _site_id()
    drive_id = _drive_id(token, site_id)
    resp = requests.get(
        f"{_GRAPH_BASE}/drives/{drive_id}/items/{item_id}/content",
        headers={"Authorization": f"Bearer {token}"},
        timeout=120,
        allow_redirects=True,
    )
    resp.raise_for_status()
    return resp.content


def get_file_metadata(item_id: str) -> dict[str, Any]:
    token = _get_token()
    site_id = _site_id()
    drive_id = _drive_id(token, site_id)
    resp = requests.get(
        f"{_GRAPH_BASE}/drives/{drive_id}/items/{item_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def copy_to_locked_folder(item_id: str, audit_id: int, evidence_id: int) -> str:
    token = _get_token()
    site_id = _site_id()
    drive_id = _drive_id(token, site_id)
    dest_path = f"{_LOCKED_FOLDER}/{audit_id}/{evidence_id}"

    # Get source item name
    meta = get_file_metadata(item_id)
    name = meta.get("name", f"evidence_{evidence_id}")

    resp = requests.post(
        f"{_GRAPH_BASE}/drives/{drive_id}/items/{item_id}/copy",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "parentReference": {"driveId": drive_id, "path": f"/root:/{dest_path}"},
            "name": name,
        },
        timeout=60,
    )
    resp.raise_for_status()
    # Copy is async; return a composite URL for now - callers should poll the monitor URL
    monitor_url = resp.headers.get("Location", "")
    return monitor_url


def get_download_url(item_id: str) -> str:
    """Return a proxied content URL. Does not use createLink sharing links."""
    token = _get_token()
    site_id = _site_id()
    drive_id = _drive_id(token, site_id)
    resp = requests.get(
        f"{_GRAPH_BASE}/drives/{drive_id}/items/{item_id}",
        headers={"Authorization": f"Bearer {token}"},
        params={"select": "@microsoft.graph.downloadUrl,webUrl"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("@microsoft.graph.downloadUrl") or data.get("webUrl", "")


class SharePointIntegration(IntegrationBase):
    name = "sharepoint"

    def health_check(self) -> bool:
        try:
            _get_token()
            return True
        except Exception:
            return False

    def sync(self, db: Session) -> IntegrationRunResult:
        run = self._start_run(db)
        try:
            token = _get_token()
            site_id = _site_id()
            drive_id = _drive_id(token, site_id)

            resp = requests.get(
                f"{_GRAPH_BASE}/drives/{drive_id}/root:/{_EVIDENCE_FOLDER}:/children",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30,
            )
            if resp.status_code == 404:
                result = IntegrationRunResult(
                    integration_name=self.name, status="success", records_synced=0
                )
                self._finish_run(db, run, result)
                db.commit()
                return result

            resp.raise_for_status()
            items = resp.json().get("value", [])

            snapshots = [
                {
                    "resource_type": "drive_item",
                    "resource_id": item["id"],
                    "data": {
                        "name": item.get("name"),
                        "size": item.get("size"),
                        "webUrl": item.get("webUrl"),
                        "lastModifiedDateTime": item.get("lastModifiedDateTime"),
                    },
                }
                for item in items
            ]
            count = self._write_snapshots(db, run, snapshots)
            result = IntegrationRunResult(
                integration_name=self.name, status="success", records_synced=count
            )
        except Exception as exc:
            logger.exception("SharePoint sync failed")
            result = IntegrationRunResult(
                integration_name=self.name, status="failed", error_message=str(exc)
            )

        self._finish_run(db, run, result)
        db.commit()
        return result
