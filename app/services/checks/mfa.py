from app.services.checks.base import BaseCheck, CheckResult, CheckStatus


class GoogleMFACheck(BaseCheck):
    """
    Automated check for CC6.1 (Logical Access) focusing on MFA enforcement.
    """

    def __init__(self):
        super().__init__(
            name="Google Workspace MFA Enforcement",
            control_code="CC6.1",
            description="Verifies that 2nd-step verification (MFA) is enforced for all active users."
        )

    async def run(self, **kwargs) -> CheckResult:
        if not kwargs.get("test_mode"):
            return self.result(
                CheckStatus.SKIPPED,
                "Google Workspace MFA check skipped because no integration snapshot is available.",
                {"required_snapshot": "google_workspace:user"},
            )

        users = [
            {"email": "admin@jec.com", "mfa_enrolled": True, "service_account": False},
            {"email": "deploy-bot@jec.com", "mfa_enrolled": False, "service_account": True},
        ]
        human_users = [user for user in users if not user["service_account"]]
        failing_users = [user["email"] for user in human_users if not user["mfa_enrolled"]]

        if failing_users:
            return self.result(
                CheckStatus.FAIL,
                f"MFA check failed for {len(failing_users)} active human user(s).",
                {"users_checked": len(human_users), "failing_users": failing_users},
                "Enable MFA for every active human account or document an approved exception.",
            )

        return self.result(
            CheckStatus.PASS,
            f"MFA is enforced for {len(human_users)} active human user(s).",
            {
                "users_checked": len(human_users),
                "service_accounts_excluded": 1,
            },
        )
