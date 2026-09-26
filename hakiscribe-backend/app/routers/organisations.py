"""Production firm onboarding and membership boundary."""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.services.production_auth import ProductionUser, require_production_user

router = APIRouter()


class OrganisationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)


def _client():
    try:
        from supabase import create_client
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="Supabase client is not installed") from exc
    url, key = os.environ.get("SUPABASE_URL", ""), os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        raise HTTPException(status_code=503, detail="Production database is not configured")
    return create_client(url, key)


@router.post("", status_code=201)
def create_organisation(payload: OrganisationCreate, user: ProductionUser = Depends(require_production_user)):
    """Create a firm and its first owner membership in one server-side operation."""
    client = _client()
    org = client.table("haki_organisations").insert({"name": payload.name.strip(), "created_by": user.id}).execute()
    if not org.data:
        raise HTTPException(status_code=500, detail="Could not create organisation")
    item = org.data[0]
    client.table("haki_memberships").insert({"organisation_id": item["id"], "user_id": user.id, "role": "owner", "status": "active"}).execute()
    client.table("haki_audit_events").insert({"organisation_id": item["id"], "actor_id": user.id, "event_type": "organisation_created"}).execute()
    return item


@router.get("")
def list_organisations(user: ProductionUser = Depends(require_production_user)):
    """Lists only firms where the verified user has an active membership."""
    client = _client()
    memberships = client.table("haki_memberships").select("organisation_id,role,status,haki_organisations(id,name,created_at)").eq("user_id", user.id).eq("status", "active").execute()
    return memberships.data or []
