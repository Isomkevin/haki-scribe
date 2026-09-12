import os
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
from app.routers import actions, demo, internal, matters, news, sessions, omi_webhook, stream

app = FastAPI(title="HakiScribe", version="0.1.0")

# Lovable frontend will hit this from a different origin during dev.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten before anything beyond the demo
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
app.include_router(stream.router, prefix="/sessions", tags=["stream"])
app.include_router(actions.router, prefix="/sessions", tags=["actions"])
app.include_router(omi_webhook.router, prefix="/webhooks", tags=["omi"])
app.include_router(matters.router, prefix="/matters", tags=["matters"])
app.include_router(matters.contacts_router, prefix="/contacts", tags=["contacts"])
app.include_router(internal.router, prefix="/internal", tags=["internal"])
app.include_router(demo.router, prefix="/demo", tags=["demo"])
app.include_router(news.router, prefix="/news", tags=["news"])
app.include_router(news.webhook_router, prefix="/webhooks", tags=["exa"])


@app.get("/")
def root():
    return {"service": "HakiScribe", "status": "ok", "docs": "/docs"}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "integrations": {
            "openrouter": bool(os.environ.get("OPENROUTER_API_KEY")),
            "trigger": bool(os.environ.get("TRIGGER_SECRET_KEY")),
            "exa": bool(os.environ.get("EXA_API_KEY")),
            "ambiguous": bool(os.environ.get("AMBIGUOUS_API_KEY")),
            "omi": True,
            "omi_secret": bool(os.environ.get("OMI_SHARED_SECRET")),
        },
        "environments": ["room:mic", "room:omi", "pocket:whatsapp", "desk:ambiguous", "desk:legal-intel"],
        "webhook": "/webhooks/omi?session_id=<session-uuid>",
        "exa": {
            "search": "/news/search",
            "watch": "/news/watch",
            "monitor_webhook": "/webhooks/exa",
            "mode": "legal-intelligence",
        },
    }


@app.get("/models")
def models():
    """Model picker for the 'Ask anything about this session' composer."""
    return llm_client.available_models()
