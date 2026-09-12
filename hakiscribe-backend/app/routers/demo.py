from fastapi import APIRouter, HTTPException

from app.models.schemas import SessionDetail
from app.services import showcase

router = APIRouter()


@router.post("/showcase", response_model=SessionDetail)
async def ensure_showcase():
    """Return a completed Kenyan client-meeting session for judges.

    Reuses an existing Wanjiru showcase when the library already has one;
    otherwise builds transcript, flags, privilege lock, tray, and results
    in-process so a live mic is not required.
    """
    detail, _created = await showcase.ensure_showcase()
    if detail is None:
        raise HTTPException(status_code=500, detail="The showcase session could not be built.")
    return detail
