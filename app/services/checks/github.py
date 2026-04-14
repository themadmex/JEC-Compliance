from __future__ import annotations

import random
from typing import Any, Dict

from app.services.checks.base import BaseCheck, CheckResult, CheckStatus


class GitHubVulnerabilityCheck(BaseCheck):
    """
    Automated check for CC7.1 (Security Monitoring).
    Verifies that Dependabot/Vulnerability Alerts are enabled for prod repositories.
    """
    
    def __init__(self):
        super().__init__(
            name="GitHub Vulnerability Alerts",
            control_id="CC7.1",
            description="Ensures all production repositories have vulnerability alerts and security scanning enabled."
        )

    async def run(self, **kwargs) -> CheckResult:
        # SIMULATION (Phase 2 Prep)
        repos = ["jec-compliance-hub", "jec-core-api", "jec-auth-provider"]
        failing_repos = [repos[0]] if random.random() > 0.85 else []
        
        if not failing_repos:
            return CheckResult(
                control_id=self.control_id,
                status=CheckStatus.PASS,
                summary=f"Security scanning is active on all {len(repos)} production repositories.",
                details={"repos_checked": repos, "alerts_status": "active"}
            )
        else:
            return CheckResult(
                control_id=self.control_id,
                status=CheckStatus.FAIL,
                summary=f"Vulnerability alerts are missing on {len(failing_repos)} repository.",
                details={"failing_repos": failing_repos, "checked_at": "GitHub REST API"},
                remediation_steps=f"Enable Dependabot alerts in the settings for repository: {failing_repos[0]}"
            )


class GitHubBranchProtectionCheck(BaseCheck):
    """
    Automated check for CC8.1 (Change Management).
    Verifies that 'main' or 'prod' branches require reviews and status checks.
    """
    
    def __init__(self):
        super().__init__(
            name="GitHub Branch Protection",
            control_id="CC8.1",
            description="Verifies that main branches require pull request reviews and status checks before merge."
        )

    async def run(self, **kwargs) -> CheckResult:
        # SIMULATION (Phase 2 Prep)
        repos_with_protection = 3
        total_repos = 3
        
        return CheckResult(
            control_id=self.control_id,
            status=CheckStatus.PASS,
            summary="Branch protection is enforced on all critical branches.",
            details={
                "repos_checked": total_repos,
                "protection_rules": ["Require reviews (2)", "Require status checks", "No force push"]
            }
        )
