"""Verified organisation context for production routes.

The browser may request an active organisation, but cannot assert membership;
this dependency verifies the membership with Supabase before a route uses it.
"""
from __future__ import annotations

import os
import uuid

from fastapi import Depends, Header, HTTPException
from supabase import create_client

from app.services.production_auth import ProductionUser, require_production_user


def production_client():
    """Return the server-only client used after an explicit membership check."""
    url, key = os.environ.get("SUPABASE_URL", ""), os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        raise HTTPException(status_code=503, detail="Production database is not configured")
    return create_client(url, key)


async def require_organisation(
    organisation_id: str | None = Header(default=None, alias="X-Haki-Organisation"),
    user: ProductionUser = Depends(require_production_user),
) -> tuple[ProductionUser, uuid.UUID]:
    try:
        org_id = uuid.UUID(organisation_id or "")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Select a valid organisation") from exc
    client = production_client()
    row = client.table("haki_memberships").select("role").eq("organisation_id", str(org_id)).eq("user_id", user.id).eq("status", "active").execute()
    if not row.data:
        raise HTTPException(status_code=403, detail="You do not have access to this organisation")
    return user, org_id


async def require_workspace(
    workspace_id: str | None = Header(default=None, alias="X-Haki-Workspace"),
    context: tuple[ProductionUser, uuid.UUID] = Depends(require_organisation),
) -> tuple[ProductionUser, uuid.UUID, uuid.UUID]:
    """Require a workspace belonging to the verified active organisation."""
    user, organisation_id = context
    try:
        parsed_workspace_id = uuid.UUID(workspace_id or "")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Select a valid workspace") from exc
    row = (
        production_client()
        .table("haki_workspaces")
        .select("id")
        .eq("id", str(parsed_workspace_id))
        .eq("organisation_id", str(organisation_id))
        .execute()
    )
    if not row.data:
        raise HTTPException(status_code=404, detail="Workspace not found in this organisation")
    return user, organisation_id, parsed_workspace_id


async def require_workspace_administrator(
    context: tuple[ProductionUser, uuid.UUID] = Depends(require_organisation),
) -> tuple[ProductionUser, uuid.UUID]:
    """Restrict firm-wide workspace administration to owners and admins."""
    user, organisation_id = context
    result = (
        production_client().table("haki_memberships").select("role")
        .eq("organisation_id", str(organisation_id)).eq("user_id", user.id)
        .eq("status", "active").in_("role", ["owner", "admin"]).execute()
    )
    if not result.data:
        raise HTTPException(status_code=403, detail="Workspace administration requires an owner or administrator role")
    if user.aal != "aal2":
        raise HTTPException(status_code=403, detail="Set up and verify two-factor authentication before administering workspaces")
    return user, organisation_id


def require_session_access(client, session_id: uuid.UUID, organisation_id: uuid.UUID, user_id: str) -> dict:
    """Enforce matter-level access because server-side workers bypass RLS."""
    result = client.table("haki_sessions").select("*").eq("id", str(session_id)).execute()
    if not result.data or result.data[0]["organisation_id"] != str(organisation_id):
        raise HTTPException(status_code=404, detail="Session not found")
    session = result.data[0]
    if session.get("matter_id"):
        membership = (
            client.table("haki_matter_memberships")
            .select("matter_id")
            .eq("matter_id", session["matter_id"])
            .eq("user_id", user_id)
            .execute()
        )
        if not membership.data:
            raise HTTPException(status_code=403, detail="You do not have access to this matter")
    return session
