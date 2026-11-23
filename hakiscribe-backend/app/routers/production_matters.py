"""Org-scoped matters and contacts under /production/matters and /production/contacts."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from app.models.schemas import Contact, ContactCreate, ContactUpdate, ContactWithSessions, Matter, MatterCreate
from app.services.production_auth import require_csrf
from app.services.production_matters import ProductionMattersRepo
from app.services.tenant_context import production_client, require_organisation, require_workspace

router = APIRouter()
contacts_router = APIRouter()


def _repo(context) -> ProductionMattersRepo:
    user, organisation_id = context[0], context[1]
    return ProductionMattersRepo(production_client(), organisation_id, user.id)


@router.get("", response_model=list[Matter])
async def list_matters(context=Depends(require_organisation)):
    return _repo(context).list_matters()


@router.post("", response_model=Matter)
async def create_matter(
    payload: MatterCreate,
    context=Depends(require_workspace),
    _csrf: None = Depends(require_csrf),
):
    return _repo(context).create_matter(
        client_name=payload.client_name,
        matter_name=payload.matter_name,
        workspace_id=context[2],
        session_id=payload.session_id,
    )


@router.get("/{matter_id}", response_model=Matter)
async def get_matter(matter_id: UUID, context=Depends(require_organisation)):
    return _repo(context).get_matter(matter_id)


@router.get("/{matter_id}/contacts", response_model=list[Contact])
async def list_matter_contacts(matter_id: UUID, context=Depends(require_organisation)):
    repo = _repo(context)
    repo.get_matter(matter_id)
    return repo.list_contacts(matter_id=matter_id)


@router.post("/{matter_id}/contacts", response_model=Contact)
async def add_matter_contact(
    matter_id: UUID,
    payload: ContactCreate,
    context=Depends(require_organisation),
    _csrf: None = Depends(require_csrf),
):
    return _repo(context).create_contact(
        name=payload.name, updates=payload.updates, matter_id=matter_id, session_id=payload.session_id
    )


@contacts_router.get("", response_model=list[ContactWithSessions])
async def list_contacts(context=Depends(require_organisation)):
    return _repo(context).list_contacts()


@contacts_router.post("", response_model=Contact)
async def create_contact(
    payload: ContactCreate,
    context=Depends(require_organisation),
    _csrf: None = Depends(require_csrf),
):
    return _repo(context).create_contact(
        name=payload.name, updates=payload.updates, matter_id=payload.matter_id, session_id=payload.session_id
    )


@contacts_router.get("/{contact_id}", response_model=ContactWithSessions)
async def get_contact(contact_id: UUID, context=Depends(require_organisation)):
    return _repo(context).get_contact(contact_id)


@contacts_router.patch("/{contact_id}", response_model=ContactWithSessions)
async def update_contact(
    contact_id: UUID,
    payload: ContactUpdate,
    context=Depends(require_organisation),
    _csrf: None = Depends(require_csrf),
):
    return _repo(context).update_contact(
        contact_id,
        name=payload.name,
        updates=payload.updates,
        matter_id=payload.matter_id,
        clear_matter=payload.clear_matter,
        session_ids=payload.session_ids,
    )
