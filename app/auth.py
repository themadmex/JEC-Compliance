from __future__ import annotations

import os
from typing import Any

import msal
from fastapi import Cookie, HTTPException, status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

TENANT_ID = os.environ.get("AZURE_TENANT_ID", "")
CLIENT_ID = os.environ.get("AZURE_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET", "")
SESSION_SECRET = os.environ.get("SESSION_SECRET_KEY", "dev-secret-change-me")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["User.Read"]

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
        return decode_session_token(session)
    except (SignatureExpired, BadSignature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
