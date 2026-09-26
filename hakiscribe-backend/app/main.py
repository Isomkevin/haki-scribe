import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

def _load_env_files() -> None:
    root = Path(__file__).resolve().parents[1]
    for name in (".env", ".env.local"):
        path = root / name
        if not path.exists():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.split("#", 1)[0].strip()
            if not line or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key, value = key.strip(), value.strip().strip('"').strip("'")
            if not key:
                continue
            override = name.endswith(".local")
            if not value and not override:
                continue
            if override or key not in os.environ:
                os.environ[key] = value


_load_env_files()

from app.integrations import llm_client
from app.routers import (
    chats,
    actions,
    auth,
    demo,
    integrations,
    internal,
    matters,
    news,
    sessions,
    omi_webhook,
    stream,
)
from app.services import demo_library


@asynccontextmanager
async def lifespan(_app: FastAPI):
    task = asyncio.create_task(demo_library.bootstrap_demo_library())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="HakiScribe", version="0.1.0", lifespan=lifespan)

# Lovable frontend will hit this from a different origin during dev.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten before anything beyond the demo
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
app.include_router(stream.router, prefix="/sessions", tags=["stream"])
app.include_router(actions.router, prefix="/sessions", tags=["actions"])
app.include_router(chats.router, prefix="/sessions", tags=["chats"])
app.include_router(omi_webhook.router, prefix="/webhooks", tags=["omi"])
app.include_router(matters.router, prefix="/matters", tags=["matters"])
app.include_router(matters.contacts_router, prefix="/contacts", tags=["contacts"])
app.include_router(internal.router, prefix="/internal", tags=["internal"])
app.include_router(demo.router, prefix="/demo", tags=["demo"])
app.include_router(news.router, prefix="/news", tags=["news"])
app.include_router(news.webhook_router, prefix="/webhooks", tags=["exa"])
app.include_router(integrations.router, prefix="/integrations", tags=["integrations"])


@app.get("/")
def root():
    return {"service": "HakiScribe", "status": "ok", "docs": "/docs"}


@app.get("/health")
async def health():
    from app.integrations import ambiguous_client
    from app.services import db, integrations, object_store, omi_pairing

    omi_linked = bool(omi_pairing.linked_uid())
    return {
        "status": "ok",
        "storage": {"database": db.status(), "documents": object_store.status()},
        "integrations": {
            "openrouter": bool(integrations.get_creds("openrouter")),
            "intron": bool(integrations.get_creds("intron")),
            "trigger": bool(os.environ.get("TRIGGER_SECRET_KEY")),
            "exa": bool(os.environ.get("EXA_API_KEY")),
            "ambiguous": ambiguous_client.configured(),
            "ambiguous_ok": await ambiguous_client.ping() if ambiguous_client.configured() else False,
            "omi": omi_linked,
            "omi_linked": omi_linked,
            "omi_secret": bool(os.environ.get("OMI_SHARED_SECRET")),
        },
        "environments": ["room:mic", "room:omi", "pocket:whatsapp", "desk:ambiguous", "desk:legal-intel"],
        "webhook": "/webhooks/omi?session_id=<session-uuid>",
        "omi_miniapp": {
            "webhook_url": omi_pairing.webhook_url(),
            "auth_url": omi_pairing.auth_url(),
            "setup_completed_url": omi_pairing.setup_completed_url(),
            "linked": omi_linked,
        },
        "exa": {
            "search": "/news/search",
            "watch": "/news/watch",
            "monitor_webhook": "/webhooks/exa",
            "monitor_webhook_url": (
                os.environ.get("EXA_MONITOR_WEBHOOK_URL")
                or f"{(os.environ.get('BACKEND_INTERNAL_URL') or '').rstrip('/')}/webhooks/exa"
            ),
            "mode": "legal-intelligence",
        },
    }


@app.get("/models")
def models():
    """Model picker for the 'Ask anything about this session' composer.
    Includes built-in OpenRouter models plus any user-connected LLM keys."""
    base = llm_client.available_models()
    from app.services import integrations
    connected = integrations.connected_llm_models()
    seen = {item["id"] for item in connected}
    merged = list(connected)
    for item in base.get("models") or []:
        if isinstance(item, dict) and item.get("id") not in seen:
            merged.append(item)
            seen.add(str(item.get("id")))
    base["models"] = merged
    return base
