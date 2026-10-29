from pydantic import BaseModel

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import SessionDetail, SessionLibraryItem
from app.services import demo_library, live_nemotron_demo, showcase

router = APIRouter()


class DemoSyncResult(BaseModel):
    created: int
    reused: int
    completing: bool
    sessions: list[SessionLibraryItem]


@router.post("/live-nemotron", response_model=SessionDetail)
async def ensure_live_nemotron(rebuild: bool = Query(default=False)):
    """Short Kilimani intake for a live Nebius Token Factory demo.

    Speakers and privilege are already set. Detected actions and drafts are
    intentionally empty — the judge clicks Detect then Generate so Nemotron
    Super / Ultra and Tavily run at request time. Pass rebuild=true to clear
    a previous tray and restore the short transcript.
    """
    detail, _created = await live_nemotron_demo.ensure_live_nemotron_demo(rebuild=rebuild)
    if detail is None:
        raise HTTPException(status_code=500, detail="The live Nemotron demo session could not be built.")
    return detail


@router.post("/showcase", response_model=SessionDetail)
async def ensure_showcase(rebuild: bool = Query(default=False)):
    """Return a completed Kenyan client-meeting session (saved sample).

    Prefer POST /demo/live-nemotron for the Nebius hackathon demo — that path
    forces live Token Factory calls. This showcase may reuse pre-generated
    results and a long padded catalog transcript.
    """
    detail, _created = await showcase.ensure_showcase(rebuild=rebuild)
    if detail is None:
        raise HTTPException(status_code=500, detail="The showcase session could not be built.")
    return detail


@router.post("/sahara", response_model=SessionDetail)
async def ensure_sahara_demo(rebuild: bool = Query(default=False)):
    """Seed multilingual / code-switch demo sessions and open the primary court hearing.

    Sessions use ordinary desk titles across existing matters; transcripts are
    seeded as Sahara legal refine output. No microphone or live Intron key required.
    """
    detail, _created = await demo_library.ensure_sahara_demo(rebuild=rebuild)
    if detail is None:
        raise HTTPException(status_code=500, detail="The multilingual demo sessions could not be built.")
    return detail


@router.post("/sync", response_model=DemoSyncResult)
async def sync_demo_library():
    """Restore every seed matter and session that is missing from the desk.

    Fast path creates transcripts immediately. Detect/generate continues in
    the background so Render request limits are not hit.
    """
    return DemoSyncResult(**await demo_library.sync_demo_library())
