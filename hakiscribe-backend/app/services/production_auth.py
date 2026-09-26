"""Supabase-backed identity boundary for production routes.

Demo routes retain the legacy signed-token flow. Production routes call
``require_production_user`` and never trust an organisation id from the client.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import httpx
from fastapi import Header, HTTPException


@dataclass(frozen=True)
class ProductionUser:
    id: str
    email: str
    email_confirmed: bool


def production_auth_enabled() -> bool:
    return (os.environ.get("HAKISCRIBE_PRODUCTION_AUTH") or "false").strip().lower() in {"1", "true", "yes", "on"}


async def require_production_user(authorization: str | None = Header(default=None)) -> ProductionUser:
    if not production_auth_enabled():
        raise HTTPException(status_code=503, detail="Production authentication is not enabled")
    token = (authorization or "").removeprefix("Bearer ").strip()
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
    return ProductionUser(id=user_id, email=email, email_confirmed=True)
