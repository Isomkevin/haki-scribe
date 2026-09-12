from fastapi import APIRouter

from app.models.schemas import Matter, MatterCreate
from app.services import storage

router = APIRouter()


@router.post("", response_model=Matter)
def create_matter(payload: MatterCreate):
    """Usually created as a side effect of generating a workspace_matter
    action, but exposed directly too — e.g. to pre-seed existing clients
    so day-one detection already recognizes them."""
    matter = Matter(**payload.model_dump())
    return storage.create_matter(matter)


@router.get("", response_model=list[Matter])
def list_matters():
    return storage.list_matters()
