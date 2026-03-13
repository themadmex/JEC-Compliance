from __future__ import annotations

import os
from typing import Any, Callable

import msal
from fastapi import Cookie, HTTPException, status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.db import get_connection

TENANT_ID = os.environ.get("AZURE_TENANT_ID", "")
CLIENT_ID = os.environ.get("AZURE_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET", "")
SESSION_SECRET = os.environ.get("SESSION_SECRET_KEY", "dev-secret-change-me")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["User.Read"]
ROLE_ORDER = {
    "viewer": 0,
    "contributor": 1,
    "security_reviewer": 2,
    "compliance_manager": 3,
    "admin": 4,
}

_msal_app: msal.ConfidentialClientApplication | None = None


def get_msal_app() -> msal.ConfidentialClientApplication:
    global _msal_app
    if _msal_app is None:
        _msal_app = msal.ConfidentialClientApplication(
            CLIENT_ID,
            authority=AUTHORITY,
            client_credential=CLIENT_SECRET,
        )
    return _msal_app


_serializer: URLSafeTimedSerializer | None = None


def _get_serializer() -> URLSafeTimedSerializer:
    global _serializer
    if _serializer is None:
        _serializer = URLSafeTimedSerializer(SESSION_SECRET)
    return _serializer


def create_session_token(user: dict[str, Any]) -> str:
    return _get_serializer().dumps(user, salt="session")


def decode_session_token(token: str) -> dict[str, Any]:
    return _get_serializer().loads(token, salt="session", max_age=86400 * 7)


def get_current_user(session: str | None = Cookie(default=None)) -> dict[str, Any]:
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = decode_session_token(session)
    except (SignatureExpired, BadSignature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

    oid = payload.get("oid")
    if not oid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")

    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, oid, email, name, role FROM users WHERE oid = ?",
            (oid,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return dict(row)


def require_role(min_role: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
    if min_role not in ROLE_ORDER:
        raise ValueError(f"Unsupported role: {min_role}")

    def dependency(session: str | None = Cookie(default=None)) -> dict[str, Any]:
        user = get_current_user(session)
        if ROLE_ORDER.get(user["role"], -1) < ROLE_ORDER[min_role]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return user

    return dependency
