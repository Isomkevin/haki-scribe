from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import actions, internal, matters, sessions, omi_webhook, stream

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


@app.get("/")
def root():
    return {"service": "HakiScribe", "status": "ok", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}
