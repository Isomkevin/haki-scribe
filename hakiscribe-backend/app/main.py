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
    court_webhooks,
    demo,
    hearings,
    integrations,
    internal,
    matters,
    news,
    sessions,
    omi_webhook,
    organisations,
    production_actions,
    production_auth,
    production_chats,
    production_hearings,
    production_matters,
    production_sessions,
    stream,
)
from app.services import demo_library, hearing_jobs
from app.services.production_auth import production_auth_ready, production_configuration_issues


@asynccontextmanager
async def lifespan(_app: FastAPI):
    task = asyncio.create_task(demo_library.bootstrap_demo_library())
    worker = None
    if hearing_jobs.worker_enabled() and (
        not production_auth_enabled_flag or (os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_KEY"))
    ):
        worker = hearing_jobs.JobWorker()
        worker.start()
    try:
        yield
    finally:
        if worker is not None:
            await worker.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="HakiScribe", version="0.1.0", lifespan=lifespan)

production_auth_enabled_flag = os.environ.get("HAKISCRIBE_PRODUCTION_AUTH", "false").lower() == "true"
allowed_origins = [
    origin.strip()
    for origin in os.environ.get("HAKISCRIBE_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
# Demo keeps its convenient local cross-origin setup. A production deployment
# has no browser CORS access until its exact frontend origins are configured.
cors_origins = allowed_origins if production_auth_enabled_flag else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=production_auth_enabled_flag,
    allow_methods=["*"],
    allow_headers=["*"],
)

if production_auth_enabled_flag:
    # Mounted before production_sessions: its GET /production/{session_id} would
    # otherwise capture /production/hearings, /production/matters and
    # /production/contacts and answer 422 (not a UUID).
    app.include_router(
        production_hearings.router,
        prefix="/production/hearings",
        tags=["production-hearings"],
    )
    app.include_router(production_matters.router, prefix="/production/matters", tags=["production-matters"])
    app.include_router(production_matters.contacts_router, prefix="/production/contacts", tags=["production-contacts"])

app.include_router(production_auth.router, prefix="/auth/production", tags=["production-auth"])
app.include_router(organisations.router, prefix="/organisations", tags=["organisations"])
app.include_router(production_actions.router, prefix="/production", tags=["production-actions"])
app.include_router(production_chats.router, prefix="/production", tags=["production-chats"])
app.include_router(production_sessions.router, prefix="/production", tags=["production"])
# Trigger.dev relays must reach the backend in both modes.
app.include_router(internal.router, prefix="/internal", tags=["internal"])
# Zoom/Teams webhooks are signed; production resolves tenant via ZOOM_HOST_ORG_MAP.
app.include_router(court_webhooks.router, prefix="/webhooks", tags=["court-webhooks"])

if not production_auth_enabled_flag:
    # Demo-era routers share in-process / snapshot storage. Production never
    # mounts them, so a missed UI migration cannot cross the tenant boundary.
    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    app.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
    app.include_router(stream.router, prefix="/sessions", tags=["stream"])
    app.include_router(actions.router, prefix="/sessions", tags=["actions"])
    app.include_router(chats.router, prefix="/sessions", tags=["chats"])
    app.include_router(omi_webhook.router, prefix="/webhooks", tags=["omi"])
    app.include_router(matters.router, prefix="/matters", tags=["matters"])
    app.include_router(matters.contacts_router, prefix="/contacts", tags=["contacts"])
    app.include_router(hearings.router, prefix="/hearings", tags=["hearings"])
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
    from app.services import ai_mode, db, inference_health, integrations, nvidia_nim, object_store, omi_pairing

    omi_linked = bool(omi_pairing.linked_uid())
    inference = await inference_health.check_all()
    return {
        "status": "ok",
        "mode": "production" if production_auth_enabled_flag else "demo",
        "ai_mode": ai_mode.describe_for_health(),
        "inference": {
            "local_whisper": inference.get("local_whisper"),
            "ollama": inference.get("ollama"),
        },
        "production_readiness": {
            "enabled": production_auth_enabled_flag,
            "ready": production_auth_ready(),
            "missing": production_configuration_issues() if production_auth_enabled_flag else [],
            "migration": "hakiscribe-backend/migrations/001_tenant_security.sql",
        },
        "storage": {"database": db.status(), "documents": object_store.status()},
        "integrations": {
            "openrouter": bool(integrations.get_creds("openrouter")),
            "intron": bool(integrations.get_creds("intron")),
            "trigger": bool(os.environ.get("TRIGGER_SECRET_KEY")) and not ai_mode.prefer_in_process_jobs(),
            "exa": bool(os.environ.get("EXA_API_KEY")),
            "ambiguous": ambiguous_client.configured(),
            "ambiguous_ok": await ambiguous_client.ping() if ambiguous_client.configured() else False,
            "omi": omi_linked,
            "omi_linked": omi_linked,
            "omi_secret": bool(os.environ.get("OMI_SHARED_SECRET")),
        },
        "nvidia_nim": await nvidia_nim.check_nvidia_nim_health(),
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


@app.get("/usage")
def usage():
    """Recent model requests for the workspace cost dashboard."""
    from app.services import llm_usage
    return llm_usage.dashboard()


@app.get("/models")
def models():
    """Model picker for the 'Ask anything about this session' composer.
    Includes built-in OpenRouter models plus any user-connected LLM keys.
    Default is Nebius Nemotron Super when the Nebius connector is live."""
    base = llm_client.available_models()
    from app.services import integrations
    from app.services import nebius as nebius_service
    connected = integrations.connected_llm_models()
    seen = {item["id"] for item in connected}
    merged = list(connected)
    for item in base.get("models") or []:
        if isinstance(item, dict) and item.get("id") not in seen:
            merged.append(item)
            seen.add(str(item.get("id")))
    base["models"] = merged
    if nebius_service.is_connected():
        base["default"] = "nebius:nemotron-super"
        base["configured"] = True
    return base
