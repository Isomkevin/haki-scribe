"""Supabase-backed identity boundary for production routes.

Demo routes retain the legacy signed-token flow. Production routes call
``require_production_user`` and never trust an organisation id from the client.
"""
from __future__ import annotations

import os
import base64
import json
import secrets
from dataclasses import dataclass

import httpx
from fastapi import Cookie, Header, HTTPException


@dataclass(frozen=True)
class ProductionUser:
    id: str
    email: str
    email_confirmed: bool
    aal: str = "aal1"


def production_auth_enabled() -> bool:
    return (os.environ.get("HAKISCRIBE_PRODUCTION_AUTH") or "false").strip().lower() in {"1", "true", "yes", "on"}


def production_configuration_issues() -> list[str]:
    """Safe, non-secret checklist for enabling the production surface."""
    required = {
        "SUPABASE_URL": os.environ.get("SUPABASE_URL"),
        "SUPABASE_ANON_KEY": os.environ.get("SUPABASE_ANON_KEY"),
        "SUPABASE_SERVICE_KEY": os.environ.get("SUPABASE_SERVICE_KEY"),
        "HAKISCRIBE_ALLOWED_ORIGINS": os.environ.get("HAKISCRIBE_ALLOWED_ORIGINS"),
        "HAKISCRIBE_PASSWORD_RESET_URL": os.environ.get("HAKISCRIBE_PASSWORD_RESET_URL"),
    }
    return [name for name, value in required.items() if not (value or "").strip()]


def production_auth_ready() -> bool:
    return production_auth_enabled() and not production_configuration_issues()


def csrf_token() -> str:
    return secrets.token_urlsafe(32)


def _token_aal(token: str) -> str:
    """Read the assurance claim after the same token was verified by Auth."""
    try:
        encoded = token.split(".")[1]
        encoded += "=" * (-len(encoded) % 4)
        claims = json.loads(base64.urlsafe_b64decode(encoded))
        return "aal2" if claims.get("aal") == "aal2" else "aal1"
    except (IndexError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return "aal1"


def auth_headers(access_token: str) -> dict[str, str]:
    api_key = os.environ.get("SUPABASE_ANON_KEY") or ""
    if not api_key:
        raise HTTPException(status_code=503, detail="Production identity is not configured")
    return {"Authorization": f"Bearer {access_token}", "apikey": api_key}


async def require_production_user(
    authorization: str | None = Header(default=None),
    access_token: str | None = Cookie(default=None, alias="hakiscribe_access_token"),
) -> ProductionUser:
    if not production_auth_enabled():
        raise HTTPException(status_code=503, detail="Production authentication is not enabled")
    if production_configuration_issues():
        raise HTTPException(status_code=503, detail="Production authentication is not fully configured")
    token = (authorization or "").removeprefix("Bearer ").strip() or (access_token or "")
    url = (os.environ.get("SUPABASE_URL") or "").rstrip("/")
    api_key = os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_SERVICE_KEY") or ""
    if not token or not url or not api_key:
        raise HTTPException(status_code=401, detail="Sign in to continue")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"{url}/auth/v1/user",
                headers={"Authorization": f"Bearer {token}", "apikey": api_key},
            )
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Sign in to continue")
        data = response.json()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Identity service is unavailable") from exc
    user_id, email = str(data.get("id") or ""), str(data.get("email") or "")
    if not user_id or not email or not data.get("email_confirmed_at"):
        raise HTTPException(status_code=403, detail="Verify your email before accessing firm data")
    return ProductionUser(id=user_id, email=email, email_confirmed=True, aal=_token_aal(token))


async def require_csrf(
    csrf_header: str | None = Header(default=None, alias="X-Haki-CSRF"),
    csrf_cookie: str | None = Cookie(default=None, alias="hakiscribe_csrf"),
) -> None:
    """Block cross-site writes when authentication is cookie based."""
    if not csrf_header or not csrf_cookie or not secrets.compare_digest(csrf_header, csrf_cookie):
        raise HTTPException(status_code=403, detail="Refresh the page and try again")
