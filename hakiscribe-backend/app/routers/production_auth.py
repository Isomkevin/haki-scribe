"""Cookie-based production account lifecycle backed by Supabase Auth.

Tokens never enter localStorage. This BFF is intentionally separate from the
legacy demo /auth/login endpoint, which must not be enabled for real users.
"""
from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from app.services.production_auth import (
    ProductionUser,
    auth_headers,
    csrf_token,
    production_auth_enabled,
    require_csrf,
    require_production_user,
)

router = APIRouter()
ACCESS_COOKIE = "hakiscribe_access_token"
REFRESH_COOKIE = "hakiscribe_refresh_token"
CSRF_COOKIE = "hakiscribe_csrf"


class PasswordLogin(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=256)


class PasswordResetRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)


class PasswordUpdate(BaseModel):
    password: str = Field(min_length=12, max_length=256)


class RecoverySession(BaseModel):
    access_token: str = Field(min_length=20, max_length=4096)
    refresh_token: str = Field(min_length=20, max_length=4096)
    expires_in: int = Field(default=900, ge=60, le=86400)


class TotpEnroll(BaseModel):
    friendly_name: str = Field(default="Authenticator", min_length=1, max_length=64)


class TotpVerify(BaseModel):
    factor_id: str = Field(min_length=1, max_length=128)
    challenge_id: str = Field(min_length=1, max_length=128)
    code: str = Field(pattern=r"^\d{6}$")


class TotpChallenge(BaseModel):
    factor_id: str = Field(min_length=1, max_length=128)


def _auth_url(path: str) -> str:
    base = (os.environ.get("SUPABASE_URL") or "").rstrip("/")
    key = os.environ.get("SUPABASE_ANON_KEY") or ""
    if not base or not key:
        raise HTTPException(status_code=503, detail="Production identity is not configured")
    return f"{base}/auth/v1{path}"


def _anon_headers() -> dict[str, str]:
    key = os.environ.get("SUPABASE_ANON_KEY") or ""
    if not key:
        raise HTTPException(status_code=503, detail="Production identity is not configured")
    return {"apikey": key, "Content-Type": "application/json"}


def _set_session_cookies(response: Response, payload: dict[str, Any]) -> str:
    access_token, refresh_token = payload.get("access_token"), payload.get("refresh_token")
    if not isinstance(access_token, str) or not isinstance(refresh_token, str):
        raise HTTPException(status_code=502, detail="Identity provider did not return a session")
    secure = production_auth_enabled()
    common = {"secure": secure, "samesite": "none" if secure else "lax", "path": "/"}
    response.set_cookie(ACCESS_COOKIE, access_token, max_age=int(payload.get("expires_in") or 900), httponly=True, **common)
    response.set_cookie(REFRESH_COOKIE, refresh_token, max_age=60 * 60 * 24 * 7, httponly=True, **common)
    csrf = csrf_token()
    response.set_cookie(CSRF_COOKIE, csrf, max_age=60 * 60 * 24 * 7, httponly=False, **common)
    return csrf


def _clear_session_cookies(response: Response) -> None:
    for name in (ACCESS_COOKIE, REFRESH_COOKIE, CSRF_COOKIE):
        response.delete_cookie(name, path="/", samesite="none" if production_auth_enabled() else "lax")


async def _post(path: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            result = await client.post(_auth_url(path), headers=headers, json=payload)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Identity service is unavailable") from exc
    if result.status_code >= 400:
        raise HTTPException(status_code=401, detail="Sign in could not be completed")
    return result.json()


async def _get(path: str, headers: dict[str, str]) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            result = await client.get(_auth_url(path), headers=headers)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Identity service is unavailable") from exc
    if result.status_code >= 400:
        raise HTTPException(status_code=401, detail="Sign in could not be completed")
    return result.json()


async def _put(path: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            result = await client.put(_auth_url(path), headers=headers, json=payload)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Identity service is unavailable") from exc
    if result.status_code >= 400:
        raise HTTPException(status_code=400, detail="Account update could not be completed")
    return result.json()


async def require_access_token(
    access_token: str | None = Cookie(default=None, alias=ACCESS_COOKIE),
) -> str:
    if not production_auth_enabled() or not access_token:
        raise HTTPException(status_code=401, detail="Sign in to continue")
    return access_token


@router.post("/login")
async def login(payload: PasswordLogin, response: Response):
    """Set Secure, HttpOnly session cookies after Supabase password sign-in."""
    if not production_auth_enabled():
        raise HTTPException(status_code=503, detail="Production authentication is not enabled")
    session = await _post("/token?grant_type=password", payload.model_dump(), _anon_headers())
    csrf = _set_session_cookies(response, session)
    user = session.get("user") or {}
    factors = await _get("/factors", auth_headers(session["access_token"]))
    verified = (factors.get("totp") or []) + (factors.get("phone") or [])
    return {"email": user.get("email"), "csrf": csrf, "mfa_required": bool(verified)}


@router.post("/refresh")
async def refresh(response: Response, refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE)):
    if not production_auth_enabled() or not refresh_token:
        raise HTTPException(status_code=401, detail="Sign in to continue")
    session = await _post("/token?grant_type=refresh_token", {"refresh_token": refresh_token}, _anon_headers())
    csrf = _set_session_cookies(response, session)
    return {"csrf": csrf}


@router.post("/recovery-session")
async def establish_recovery_session(payload: RecoverySession, response: Response):
    """Convert the short-lived token from a reset-link URL fragment to cookies.

    The token is posted once over HTTPS and is never persisted in JavaScript.
    """
    if not production_auth_enabled():
        raise HTTPException(status_code=503, detail="Production authentication is not enabled")
    await _get("/user", auth_headers(payload.access_token))
    csrf = _set_session_cookies(response, payload.model_dump())
    return {"csrf": csrf}


@router.post("/logout", status_code=204)
async def logout(response: Response, _csrf: None = Depends(require_csrf)):
    _clear_session_cookies(response)


@router.get("/me")
async def me(user: ProductionUser = Depends(require_production_user)):
    return {"id": user.id, "email": user.email, "email_confirmed": user.email_confirmed, "aal": user.aal}


@router.post("/password-reset", status_code=202)
async def request_password_reset(payload: PasswordResetRequest):
    """Always return the same response to avoid revealing registered emails."""
    reset_url = os.environ.get("HAKISCRIBE_PASSWORD_RESET_URL") or ""
    if not reset_url:
        raise HTTPException(status_code=503, detail="Password reset is not configured")
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            await client.post(_auth_url("/recover"), headers=_anon_headers(), json={"email": payload.email, "redirect_to": reset_url})
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Identity service is unavailable") from exc
    return {"message": "If an account exists, a reset link has been sent."}


@router.put("/password")
async def update_password(
    payload: PasswordUpdate,
    response: Response,
    access_token: str = Depends(require_access_token),
    _user: ProductionUser = Depends(require_production_user),
    _csrf: None = Depends(require_csrf),
):
    await _put("/user", {"password": payload.password}, auth_headers(access_token))
    # Password changes are a sensitive session boundary. Require a fresh login.
    _clear_session_cookies(response)
    return {"message": "Password updated. Sign in again on this device."}


@router.post("/mfa/totp/enroll")
async def enroll_totp(
    payload: TotpEnroll,
    access_token: str = Depends(require_access_token),
    _user: ProductionUser = Depends(require_production_user),
    _csrf: None = Depends(require_csrf),
):
    return await _post("/factors", {"factor_type": "totp", "friendly_name": payload.friendly_name}, auth_headers(access_token))


@router.get("/mfa/factors")
async def list_mfa_factors(
    access_token: str = Depends(require_access_token),
    _user: ProductionUser = Depends(require_production_user),
):
    return await _get("/factors", auth_headers(access_token))


@router.post("/mfa/totp/challenge")
async def challenge_totp(
    payload: TotpChallenge,
    access_token: str = Depends(require_access_token),
    _user: ProductionUser = Depends(require_production_user),
    _csrf: None = Depends(require_csrf),
):
    return await _post(f"/factors/{payload.factor_id}/challenge", {}, auth_headers(access_token))


@router.post("/mfa/totp/verify")
async def verify_totp(
    payload: TotpVerify,
    response: Response,
    access_token: str = Depends(require_access_token),
    _user: ProductionUser = Depends(require_production_user),
    _csrf: None = Depends(require_csrf),
):
    result = await _post(
        f"/factors/{payload.factor_id}/verify",
        {"challenge_id": payload.challenge_id, "code": payload.code},
        auth_headers(access_token),
    )
    csrf = _set_session_cookies(response, result)
    return {"csrf": csrf, "aal": "aal2"}
