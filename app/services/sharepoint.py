from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

import msal

TENANT_ID = os.environ.get("AZURE_TENANT_ID", "")
CLIENT_ID = os.environ.get("AZURE_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET", "")
SHAREPOINT_SITE_URL = os.environ.get("SHAREPOINT_SITE_URL", "")

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def _encode_path(path: str) -> str:
    """Percent-encode a SharePoint drive path, preserving forward slashes."""
    return urllib.parse.quote(path, safe="/")

# Module-level caches — populated on first use
_site_id: str | None = None
_drive_id: str | None = None
_msal_app: msal.ConfidentialClientApplication | None = None


def is_configured() -> bool:
    return bool(SHAREPOINT_SITE_URL and TENANT_ID and CLIENT_ID and CLIENT_SECRET)


def _get_msal_app() -> msal.ConfidentialClientApplication:
    global _msal_app
    if _msal_app is None:
        _msal_app = msal.ConfidentialClientApplication(
            CLIENT_ID,
            authority=f"https://login.microsoftonline.com/{TENANT_ID}",
            client_credential=CLIENT_SECRET,
        )
    return _msal_app


def _get_app_token() -> str:
    """Acquire app-only Microsoft Graph token (cached by MSAL for ~1 hour)."""
    result = _get_msal_app().acquire_token_for_client(
        scopes=["https://graph.microsoft.com/.default"]
    )
    if "access_token" not in result:
        raise RuntimeError(
            f"Graph token error: {result.get('error_description', result.get('error', 'unknown'))}"
        )
    return result["access_token"]


def _graph_get(path: str) -> dict[str, Any]:
    token = _get_app_token()
    req = urllib.request.Request(
        url=f"{GRAPH_BASE}{path}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _graph_post(path: str, body: dict[str, Any]) -> dict[str, Any]:
    token = _get_app_token()
    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url=f"{GRAPH_BASE}{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        data=payload,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 409:
            return {"_already_exists": True}
        raise


def _graph_put(path: str, data: bytes, content_type: str) -> dict[str, Any]:
    token = _get_app_token()
    req = urllib.request.Request(
        url=f"{GRAPH_BASE}{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": content_type,
        },
        data=data,
        method="PUT",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _resolve_site_id() -> str:
    global _site_id
    if _site_id:
        return _site_id
    from urllib.parse import urlparse

    parsed = urlparse(SHAREPOINT_SITE_URL.rstrip("/"))
    hostname = parsed.hostname
    path = parsed.path.rstrip("/")
    data = _graph_get(f"/sites/{hostname}:{path}")
    _site_id = data["id"]
    return _site_id


def _resolve_drive_id(site_id: str, library: str = "Documents") -> str:
    global _drive_id
    if _drive_id:
        return _drive_id
    data = _graph_get(f"/sites/{site_id}/drives")
    for drive in data.get("value", []):
        if drive.get("name") == library:
            _drive_id = drive["id"]
            return _drive_id
    # Fall back to first drive if named one not found
    drives = data.get("value", [])
    if not drives:
        raise RuntimeError(f"No drives found on SharePoint site {SHAREPOINT_SITE_URL}")
    _drive_id = drives[0]["id"]
    return _drive_id


def _get_site_and_drive() -> tuple[str, str]:
    site_id = _resolve_site_id()
    drive_id = _resolve_drive_id(site_id)
    return site_id, drive_id


# ── Public API ────────────────────────────────────────────────────────────────


def browse_files(folder_path: str = "") -> list[dict[str, Any]]:
    """List files and folders in a SharePoint document library path."""
    site_id, drive_id = _get_site_and_drive()
    if folder_path:
        encoded = _encode_path(folder_path.strip("/"))
        endpoint = f"/sites/{site_id}/drives/{drive_id}/root:/{encoded}:/children"
    else:
        endpoint = f"/sites/{site_id}/drives/{drive_id}/root/children"
    data = _graph_get(endpoint)
    return [
        {
            "id": item.get("id"),
            "name": item.get("name"),
            "size": item.get("size"),
            "last_modified": item.get("lastModifiedDateTime"),
            "web_url": item.get("webUrl"),
            "is_folder": "folder" in item,
            "mime_type": item.get("file", {}).get("mimeType"),
        }
        for item in data.get("value", [])
    ]


def upload_file(
    filename: str,
    content: bytes,
    content_type: str,
    folder: str = "Compliance",
) -> dict[str, Any]:
    """Upload a file to SharePoint. Returns metadata including web_url."""
    site_id, drive_id = _get_site_and_drive()
    remote_path = f"{folder}/{filename}" if folder else filename
    result = _graph_put(
        f"/sites/{site_id}/drives/{drive_id}/root:/{_encode_path(remote_path)}:/content",
        content,
        content_type,
    )
    return {
        "sharepoint_id": result.get("id"),
        "name": result.get("name"),
        "web_url": result.get("webUrl"),
        "size": result.get("size"),
    }


def get_file_metadata(item_id: str) -> dict[str, Any]:
    """Get metadata for a specific SharePoint file by item ID."""
    site_id, drive_id = _get_site_and_drive()
    data = _graph_get(f"/sites/{site_id}/drives/{drive_id}/items/{item_id}")
    return {
        "id": data.get("id"),
        "name": data.get("name"),
        "web_url": data.get("webUrl"),
        "size": data.get("size"),
        "last_modified": data.get("lastModifiedDateTime"),
    }


def download_file(item_id: str) -> bytes:
    """Download raw file bytes for a specific SharePoint file by item ID."""
    site_id, drive_id = _get_site_and_drive()
    token = _get_app_token()
    req = urllib.request.Request(
        url=f"{GRAPH_BASE}/sites/{site_id}/drives/{drive_id}/items/{item_id}/content",
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def get_lists() -> list[dict[str, Any]]:
    """List all visible SharePoint Lists on the site."""
    site_id = _resolve_site_id()
    data = _graph_get(f"/sites/{site_id}/lists?$filter=list/hidden eq false")
    return [
        {
            "id": lst.get("id"),
            "name": lst.get("name"),
            "display_name": lst.get("displayName"),
            "web_url": lst.get("webUrl"),
        }
        for lst in data.get("value", [])
    ]


def get_list_items(list_name: str) -> list[dict[str, Any]]:
    """Get all items from a SharePoint List, returning the fields dict per item."""
    site_id = _resolve_site_id()
    data = _graph_get(f"/sites/{site_id}/lists/{list_name}/items?expand=fields&$top=500")
    return [item.get("fields", {}) for item in data.get("value", [])]


# Folder tree mirroring the left sidebar navigation
_FOLDER_STRUCTURE: dict[str, list[str]] = {
    "Compliance": ["Frameworks", "Controls", "Policies", "Documents", "Audits"],
    "Customer Trust": ["Accounts", "Trust Center", "Knowledge Base", "Activity"],
    "Risk": ["Risks", "Risk Library", "Action Tracker", "Snapshots"],
    "Vendors": [],
    "Assets": ["Inventory", "Code Changes", "Vulnerabilities", "Security Alerts"],
    "Personnel": ["People", "Computers", "Access"],
}


def provision_folder_structure() -> dict[str, Any]:
    """Create the compliance folder tree on SharePoint (idempotent — skips existing folders)."""
    site_id, drive_id = _get_site_and_drive()
    created: list[str] = []
    skipped: list[str] = []
    errors: list[str] = []

    for top, subs in _FOLDER_STRUCTURE.items():
        try:
            result = _graph_post(
                f"/sites/{site_id}/drives/{drive_id}/root/children",
                {"name": top, "folder": {}, "@microsoft.graph.conflictBehavior": "fail"},
            )
            (skipped if result.get("_already_exists") else created).append(top)
        except Exception as exc:
            errors.append(f"{top}: {exc}")
            continue

        for sub in subs:
            path = f"{top}/{sub}"
            try:
                result = _graph_post(
                    f"/sites/{site_id}/drives/{drive_id}/root:/{_encode_path(top)}:/children",
                    {"name": sub, "folder": {}, "@microsoft.graph.conflictBehavior": "fail"},
                )
                (skipped if result.get("_already_exists") else created).append(path)
            except Exception as exc:
                errors.append(f"{path}: {exc}")

    return {"created": created, "skipped": skipped, "errors": errors}


def check_connection() -> dict[str, Any]:
    """Verify SharePoint connectivity. Returns status dict."""
    if not is_configured():
        return {"ok": False, "reason": "SHAREPOINT_SITE_URL not configured"}
    try:
        site_id = _resolve_site_id()
        return {"ok": True, "site_id": site_id}
    except Exception as exc:
        return {"ok": False, "reason": str(exc)}
