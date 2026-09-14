"""Sign-in endpoints for the private workspace."""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.services import auth

router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
def login(payload: LoginRequest):
    try:
        return auth.login(payload.email, payload.password)
    except auth.AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/demo")
def demo_credentials():
    """Temporary — lets the judging UI fill the demo account in one tap."""
    if not auth.demo_enabled():
        return {"enabled": False}
    account = auth.demo_account()
    return {
        "enabled": True,
        "email": account["email"],
        "password": account["password"],
        "name": account["name"],
    }


@router.get("/me")
def me(authorization: str | None = Header(default=None)):
    token = (authorization or "").removeprefix("Bearer ").strip()
    claims = auth.read_token(token)
    if not claims:
        raise HTTPException(status_code=401, detail="Sign in to continue")
    return {"email": claims.get("email"), "name": claims.get("name")}
