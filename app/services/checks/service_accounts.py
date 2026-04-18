from __future__ import annotations


SERVICE_ACCOUNT_NAME_TOKENS = (
    "bot",
    "svc",
    "service",
    "api",
    "deploy",
    "ci",
    "automation",
    "github-actions",
    "terraform",
)


def classify_service_account(account: dict, matching_personnel_email: bool = False) -> tuple[bool, str | None]:
    """Apply the v2.4 deterministic service-account candidate rule."""
    display_name = str(account.get("display_name") or account.get("name") or "").lower()
    email = str(account.get("email") or "").lower()
    last_login_days = account.get("last_login_days")

    reasons: list[str] = []
    if any(token in display_name or token in email for token in SERVICE_ACCOUNT_NAME_TOKENS):
        reasons.append("service-like name")
    if account.get("mfa_enrolled") is False:
        reasons.append("no MFA enrollment")
    if isinstance(last_login_days, int) and last_login_days > 90:
        reasons.append("no login within 90 days")
    if not matching_personnel_email:
        reasons.append("no matching personnel record")

    if len(reasons) >= 2:
        return True, "; ".join(reasons)
    return False, None
