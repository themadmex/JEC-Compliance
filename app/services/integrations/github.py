from __future__ import annotations

import logging
import os
from typing import Any

import requests
from sqlalchemy.orm import Session

from app.services.integrations.base import IntegrationBase, IntegrationRunResult

logger = logging.getLogger(__name__)

_TEST_MODE = os.environ.get("TEST_MODE", "false").lower() == "true"
_GITHUB_API = "https://api.github.com"

_FIXTURE_REPOS: list[dict[str, Any]] = [
    {
        "name": "compliance-app",
        "full_name": "jec/compliance-app",
        "id": 1001,
        "branch_protection": {
            "require_pull_request_reviews": True,
            "require_status_checks": True,
            "dismiss_stale_reviews": True,
            "restrict_pushes": False,
        },
        "dependabot_alerts": {"critical": 0, "high": 1, "medium": 2, "low": 0},
    }
]


def _headers() -> dict[str, str]:
    token = os.environ["GITHUB_TOKEN"]
    return {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}


def _fetch_repos() -> list[dict[str, Any]]:
    if _TEST_MODE:
        return _FIXTURE_REPOS

    org = os.environ["GITHUB_ORG"]
    repos: list[dict[str, Any]] = []
    page = 1
    while True:
        resp = requests.get(
            f"{_GITHUB_API}/orgs/{org}/repos",
            headers=_headers(),
            params={"per_page": 100, "page": page, "type": "all"},
            timeout=30,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        repos.extend(batch)
        page += 1

    enriched: list[dict[str, Any]] = []
    for repo in repos:
        name = repo["name"]
        bp = _fetch_branch_protection(org, name)
        alerts = _fetch_dependabot_alerts(org, name)
        enriched.append(
            {
                "name": name,
                "full_name": repo["full_name"],
                "id": repo["id"],
                "branch_protection": bp,
                "dependabot_alerts": alerts,
            }
        )
    return enriched


def _fetch_branch_protection(org: str, repo: str) -> dict[str, Any]:
    try:
        resp = requests.get(
            f"{_GITHUB_API}/repos/{org}/{repo}/branches/main/protection",
            headers=_headers(),
            timeout=30,
        )
        if resp.status_code == 404:
            return {}
        resp.raise_for_status()
        data = resp.json()
        return {
            "require_pull_request_reviews": bool(data.get("required_pull_request_reviews")),
            "require_status_checks": bool(data.get("required_status_checks")),
            "dismiss_stale_reviews": data.get("required_pull_request_reviews", {}).get(
                "dismiss_stale_reviews", False
            ),
            "restrict_pushes": bool(data.get("restrictions")),
        }
    except Exception:
        return {}


def _fetch_dependabot_alerts(org: str, repo: str) -> dict[str, int]:
    counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    try:
        resp = requests.get(
            f"{_GITHUB_API}/repos/{org}/{repo}/dependabot/alerts",
            headers=_headers(),
            params={"state": "open", "per_page": 100},
            timeout=30,
        )
        if resp.status_code in (403, 404):
            return counts
        resp.raise_for_status()
        for alert in resp.json():
            severity = alert.get("security_advisory", {}).get("severity", "low").lower()
            counts[severity] = counts.get(severity, 0) + 1
    except Exception:
        pass
    return counts


class GitHubIntegration(IntegrationBase):
    name = "github"

    def health_check(self) -> bool:
        if _TEST_MODE:
            return True
        try:
            resp = requests.get(f"{_GITHUB_API}/user", headers=_headers(), timeout=10)
            return resp.status_code == 200
        except Exception:
            return False

    def sync(self, db: Session) -> IntegrationRunResult:
        run = self._start_run(db)
        try:
            repos = _fetch_repos()
            snapshots: list[dict[str, Any]] = []
            for repo in repos:
                snapshots.append(
                    {
                        "resource_type": "repo",
                        "resource_id": str(repo["id"]),
                        "data": {
                            "name": repo["name"],
                            "full_name": repo["full_name"],
                            "branch_protection": repo["branch_protection"],
                        },
                    }
                )
                alerts = repo.get("dependabot_alerts", {})
                if any(alerts.values()):
                    snapshots.append(
                        {
                            "resource_type": "vulnerability_alert",
                            "resource_id": repo["name"],
                            "data": {"repo": repo["name"], "counts": alerts},
                        }
                    )
            count = self._write_snapshots(db, run, snapshots)
            result = IntegrationRunResult(
                integration_name=self.name, status="success", records_synced=count
            )
        except Exception as exc:
            logger.exception("GitHub sync failed")
            result = IntegrationRunResult(
                integration_name=self.name, status="failed", error_message=str(exc)
            )

        self._finish_run(db, run, result)
        db.commit()
        return result
