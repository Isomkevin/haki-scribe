from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import SessionDetail
from app.services import showcase

router = APIRouter()


@router.post("/showcase", response_model=SessionDetail)
async def ensure_showcase(rebuild: bool = Query(default=False)):
    """Return a completed Kenyan client-meeting session for judges.

    Reuses an existing Wanjiru showcase when the library already has one;
    otherwise builds transcript, flags, privilege lock, tray, and results
    in-process so a live mic is not required. Pass rebuild=true to force
    a fresh detect/generate (used after wiring Ambiguous or Trigger).
    """
    detail, _created = await showcase.ensure_showcase(rebuild=rebuild)
    if detail is None:
        raise HTTPException(status_code=500, detail="The showcase session could not be built.")
    return detail
