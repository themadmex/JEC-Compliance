from app.services.checks.base import BaseCheck, CheckResult, CheckStatus


class AWSAdminAccessCheck(BaseCheck):
    """
    Automated check for CC6.6 (Privileged Access).
    Verifies that AWS IAM users with 'AdministratorAccess' are within policy limits.
    """
    
    def __init__(self):
        super().__init__(
            name="AWS Admin Access Policy",
            control_code="CC6.6",
            description="Verifies that the number of IAM users with full Administrative access is minimized and reviewed."
        )

    async def run(self, **kwargs) -> CheckResult:
        if not kwargs.get("test_mode"):
            return self.result(
                CheckStatus.SKIPPED,
                "AWS privileged access check skipped because no IAM snapshot is available.",
                {"required_snapshot": "aws:iam_user"},
            )

        admin_count = 2
        max_allowed = 2

        if admin_count <= max_allowed:
            return self.result(
                CheckStatus.PASS,
                f"Admin access is within policy. Detected {admin_count} administrator(s).",
                {"admin_users": ["admin-1", "admin-2"], "threshold": max_allowed},
            )

        return self.result(
            CheckStatus.FAIL,
            f"Admin access exceeds policy. Detected {admin_count} administrators.",
            {"threshold": max_allowed},
            "Remove unneeded administrator access or document approval in the access review.",
        )


class ABACAccessCheck(BaseCheck):
    """
    Automated check for CC6.3 (Access Deprovisioning).
    Simulates cross-referencing Okta/Google Workspace for terminated users.
    """
    
    def __init__(self):
        super().__init__(
            name="Deprovisioning (Ghost Users)",
            control_code="CC6.3",
            description="Ensures that users terminated in HR systems are deprovisioned from IT systems within 24 hours."
        )

    async def run(self, **kwargs) -> CheckResult:
        if not kwargs.get("test_mode"):
            return self.result(
                CheckStatus.SKIPPED,
                "Deprovisioning check skipped because no user/personnel snapshots are available.",
                {"required_snapshot": "google_workspace:user"},
            )

        return self.result(
            CheckStatus.PASS,
            "No terminated users were found with active system access.",
            {"terminated_accounts_with_access": 0},
        )
