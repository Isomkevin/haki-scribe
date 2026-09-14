"""
Sign-in for the private side of HakiScribe.

Accounts are configured on the server, never in the browser:

    HAKISCRIBE_USERS="advocate@firm.co.ke:secret|Jane Advocate, clerk@firm.co.ke:other"

A temporary demo account exists for hackathon judging so a judge can open
the private workspace in one tap. Remove DEMO_LOGIN_ENABLED (or set it to
"false") to switch the demo button off everywhere — the frontend hides it
as soon as this endpoint stops offering credentials.

Tokens are HMAC-signed and stateless; there is no session table.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any, Optional

TOKEN_TTL_S = 60 * 60 * 12

DEMO_EMAIL_DEFAULT = "demo@hakiscribe.app"
DEMO_PASSWORD_DEFAULT = "hakiscribe-demo"
DEMO_NAME_DEFAULT = "Demo Advocate"

_RUNTIME_SECRET = secrets.token_urlsafe(32)


class AuthError(Exception):
    def __init__(self, message: str, status_code: int = 401) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _secret() -> bytes:
    return (os.environ.get("AUTH_SECRET") or _RUNTIME_SECRET).encode("utf-8")


def demo_enabled() -> bool:
    raw = (os.environ.get("DEMO_LOGIN_ENABLED") or "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def demo_account() -> dict[str, str]:
    return {
        "email": (os.environ.get("DEMO_EMAIL") or DEMO_EMAIL_DEFAULT).strip(),
        "password": os.environ.get("DEMO_PASSWORD") or DEMO_PASSWORD_DEFAULT,
        "name": (os.environ.get("DEMO_NAME") or DEMO_NAME_DEFAULT).strip(),
    }


def _configured_accounts() -> list[dict[str, str]]:
    """Parse HAKISCRIBE_USERS — comma separated "email:password|Display Name"."""
    raw = os.environ.get("HAKISCRIBE_USERS") or ""
    accounts: list[dict[str, str]] = []
    for chunk in raw.split(","):
        entry = chunk.strip()
        if not entry or ":" not in entry:
            continue
        credential, _, name = entry.partition("|")
        email, _, password = credential.partition(":")
        email, password = email.strip(), password.strip()
        if not email or not password:
            continue
        accounts.append({"email": email, "password": password, "name": name.strip() or email.split("@")[0]})
    return accounts


def accounts() -> list[dict[str, str]]:
    found = _configured_accounts()
    if demo_enabled():
        demo = demo_account()
        if not any(a["email"].lower() == demo["email"].lower() for a in found):
            found.append({**demo, "demo": "true"})  # type: ignore[dict-item]
    return found


def _b64(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).decode("utf-8").rstrip("=")


def _unb64(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def issue_token(email: str, name: str) -> str:
    body = json.dumps({"email": email, "name": name, "exp": int(time.time()) + TOKEN_TTL_S}, separators=(",", ":"))
    encoded = _b64(body.encode("utf-8"))
    signature = hmac.new(_secret(), encoded.encode("utf-8"), hashlib.sha256).digest()
    return f"{encoded}.{_b64(signature)}"


def read_token(token: str) -> Optional[dict[str, Any]]:
    if not token or "." not in token:
        return None
    encoded, _, signature = token.partition(".")
    expected = hmac.new(_secret(), encoded.encode("utf-8"), hashlib.sha256).digest()
    try:
        if not hmac.compare_digest(_unb64(signature), expected):
            return None
        claims = json.loads(_unb64(encoded).decode("utf-8"))
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(claims, dict) or float(claims.get("exp") or 0) < time.time():
        return None
    return claims


def login(email: str, password: str) -> dict[str, Any]:
    candidate = (email or "").strip().lower()
    if not candidate or not password:
        raise AuthError("Enter your email and password.", 400)
    for account in accounts():
        if account["email"].lower() == candidate and hmac.compare_digest(account["password"], password):
            token = issue_token(account["email"], account.get("name") or candidate)
            return {
                "token": token,
                "user": {
                    "email": account["email"],
                    "name": account.get("name") or candidate,
                    "demo": account.get("demo") == "true",
                },
            }
    raise AuthError("That email and password do not match an account on this workspace.", 401)
