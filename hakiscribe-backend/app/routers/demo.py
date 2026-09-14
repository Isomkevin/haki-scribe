from pydantic import BaseModel

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import SessionDetail, SessionLibraryItem
from app.services import demo_library, showcase

router = APIRouter()


class DemoSyncResult(BaseModel):
    created: int
    reused: int
    completing: bool
    sessions: list[SessionLibraryItem]


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


@router.post("/sync", response_model=DemoSyncResult)
async def sync_demo_library():
    """Restore every seed matter and session that is missing from the desk.

    Fast path creates transcripts immediately. Detect/generate continues in
    the background so Render request limits are not hit.
    """
    return DemoSyncResult(**await demo_library.sync_demo_library())
