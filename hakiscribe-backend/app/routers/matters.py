import uuid

from fastapi import APIRouter, HTTPException

from app.models.schemas import Contact, ContactCreate, ContactUpdate, ContactWithSessions, Matter, MatterCreate
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


def _with_sessions(contact: Contact) -> ContactWithSessions:
    return ContactWithSessions(**contact.model_dump(), session_ids=storage.contact_session_ids(contact.id))


@contacts_router.get("", response_model=list[ContactWithSessions])
def list_contacts():
    return [_with_sessions(contact) for contact in storage.list_contacts()]


@contacts_router.get("/{contact_id}", response_model=ContactWithSessions)
def get_contact(contact_id: uuid.UUID):
    contact = storage.get_contact(contact_id)
    if contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return _with_sessions(contact)


@contacts_router.patch("/{contact_id}", response_model=ContactWithSessions)
def update_contact(contact_id: uuid.UUID, payload: ContactUpdate):
    if payload.matter_id is not None and storage.get_matter(payload.matter_id) is None:
        raise HTTPException(status_code=404, detail="Matter not found")
    contact = storage.update_contact(
        contact_id,
        name=payload.name,
        updates=payload.updates,
        matter_id=payload.matter_id,
        clear_matter=payload.clear_matter,
        session_ids=payload.session_ids,
    )
    if contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return _with_sessions(contact)
