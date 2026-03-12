from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, RedirectResponse

from app.auth import SCOPES, create_session_token, get_current_user, get_msal_app
from app.repository import upsert_user

router = APIRouter(prefix="/auth", tags=["auth"])

BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:8000")
REDIRECT_URI = f"{BASE_URL}/auth/callback"


@router.get("/login")
def login() -> RedirectResponse:
    auth_url = get_msal_app().get_authorization_request_url(
        SCOPES,
        redirect_uri=REDIRECT_URI,
    )
    return RedirectResponse(auth_url)


@router.get("/callback")
def callback(code: str | None = None, error: str | None = None) -> RedirectResponse:
    if error or not code:
        return RedirectResponse("/?auth_error=1")

    result = get_msal_app().acquire_token_by_authorization_code(
        code,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )

    if "error" in result:
        return RedirectResponse("/?auth_error=1")

    claims = result.get("id_token_claims", {})
    user = upsert_user({
        "oid": claims.get("oid"),
        "email": claims.get("preferred_username") or claims.get("email", ""),
        "name": claims.get("name", ""),
    })

    token = create_session_token(user)
    response = RedirectResponse("/")
    response.set_cookie(
        "session",
        token,
        httponly=True,
        samesite="lax",
        max_age=86400 * 7,
        secure=BASE_URL.startswith("https"),
    )
    return response


@router.get("/me")
def me(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    return current_user


@router.post("/logout")
def logout() -> JSONResponse:
    response = JSONResponse({"ok": True})
    response.delete_cookie("session")
    return response
