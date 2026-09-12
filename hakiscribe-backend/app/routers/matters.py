import uuid

from fastapi import APIRouter, HTTPException

from app.models.schemas import Contact, ContactCreate, Matter, MatterCreate
from app.services import storage, workspace

router = APIRouter()
contacts_router = APIRouter()


@router.post("", response_model=Matter)
def create_matter(payload: MatterCreate):
    """Create a matter — same persistence path used when generating a
    workspace_matter action, so Session Library and /matters stay aligned."""
    matter, _ = workspace.persist_matter(
        client_name=payload.client_name,
        matter_name=payload.matter_name,
        session_id=payload.session_id,
    )
    if payload.client_name:
        workspace.persist_contact(
            name=payload.client_name,
            updates={"role": "client", "source": "matters_endpoint"},
            session_id=payload.session_id,
            matter_id=matter.id,
        )
    return matter


@router.get("", response_model=list[Matter])
def list_matters():
    return storage.list_matters()


@router.get("/{matter_id}", response_model=Matter)
def get_matter(matter_id: uuid.UUID):
    matter = storage.get_matter(matter_id)
    if matter is None:
        raise HTTPException(status_code=404, detail="Matter not found")
    return matter


@router.get("/{matter_id}/contacts", response_model=list[Contact])
def list_matter_contacts(matter_id: uuid.UUID):
    matter = storage.get_matter(matter_id)
    if matter is None:
        raise HTTPException(status_code=404, detail="Matter not found")
    return [contact for contact in storage.list_contacts() if contact.matter_id == matter.id]


@router.post("/{matter_id}/contacts", response_model=Contact)
def add_matter_contact(matter_id: uuid.UUID, payload: ContactCreate):
    matter = storage.get_matter(matter_id)
    if matter is None:
        raise HTTPException(status_code=404, detail="Matter not found")
    return workspace.persist_contact(
        name=payload.name,
        updates=payload.updates,
        session_id=payload.session_id,
        matter_id=matter.id,
    )


@contacts_router.post("", response_model=Contact)
def create_contact(payload: ContactCreate):
    return workspace.persist_contact(
        name=payload.name,
        updates=payload.updates,
        session_id=payload.session_id,
        matter_id=payload.matter_id,
    )


@contacts_router.get("", response_model=list[Contact])
def list_contacts():
    return storage.list_contacts()
