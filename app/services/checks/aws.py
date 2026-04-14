from __future__ import annotations

import random
from typing import Any, Dict

from app.services.checks.base import BaseCheck, CheckResult, CheckStatus


class AWSAdminAccessCheck(BaseCheck):
    """
    Automated check for CC6.6 (Privileged Access).
    Verifies that AWS IAM users with 'AdministratorAccess' are within policy limits.
    """
    
    def __init__(self):
        super().__init__(
            name="AWS Admin Access Policy",
            control_id="CC6.6",
            description="Verifies that the number of IAM users with full Administrative access is minimized and reviewed."
        )

    async def run(self, **kwargs) -> CheckResult:
        # SIMULATION (Phase 3 Prep)
        admin_count = 3
        max_allowed = 2
        
        if admin_count <= max_allowed:
            return CheckResult(
                control_id=self.control_id,
                status=CheckStatus.PASS,
                summary=f"Admin access is tight. Detected {admin_count} administrators.",
                details={"admin_users": ["admin-1", "admin-2", "root-backup"], "threshold": max_allowed}
            )
        else:
            return CheckResult(
                control_id=self.control_id,
                status=CheckStatus.FAIL,
                summary=f"Admin access exceeds policy. Detected {admin_count} administrators (Limit: {max_allowed}).",
                details={"violating_admins": ["user-extra-1"], "threshold": max_allowed},
                remediation_steps="Revoke 'AdministratorAccess' from user 'user-extra-1' or update the SOC 2 policy."
            )


class ABACAccessCheck(BaseCheck):
    """
    Automated check for CC6.3 (Access Deprovisioning).
    Simulates cross-referencing Okta/Google Workspace for terminated users.
    """
    
    def __init__(self):
        super().__init__(
            name="Deprovisioning (Ghost Users)",
            control_id="CC6.3",
            description="Ensures that users terminated in HR systems are deprovisioned from IT systems within 24 hours."
        )

    async def run(self, **kwargs) -> CheckResult:
        # SIMULATION (Phase 3 Prep)
        leaver_detected = random.random() > 0.9
        
        if not leaver_detected:
            return CheckResult(
                control_id=self.control_id,
                status=CheckStatus.PASS,
                summary="No ghost users detected. All system accounts map to active employees.",
                details={"okta_sync": "OK", "last_run": "Integrations API"}
            )
        else:
            return CheckResult(
                control_id=self.control_id,
                status=CheckStatus.FAIL,
                summary="Ghost user detected! System account exists for terminated employee.",
                details={"username": "malory@jec.com", "system": "GitHub", "terminated_at": "2026-04-10"},
                remediation_steps="Immediately revoke access for malory@jec.com in GitHub."
            )
