"""Probe local / private inference endpoints for health + hybrid validation."""

from __future__ import annotations

import os
from typing import Any

import httpx


def _setting(env_name: str, default: str = "") -> str:
    return (os.environ.get(env_name) or default).strip().rstrip("/")


async def _ping(url: str | None, *, path: str = "") -> dict[str, Any]:
    if not url:
        return {"configured": False, "ok": False, "url": None, "status": None, "detail": "not configured"}
    target = f"{url}{path}" if path and not url.endswith(path) else url
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(target)
        return {
            "configured": True,
            "ok": resp.status_code < 500,
            "url": target,
            "status": resp.status_code,
            "detail": "ok" if resp.status_code < 500 else resp.text[:200],
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "configured": True,
            "ok": False,
            "url": target,
            "status": None,
            "detail": str(exc)[:200],
        }


async def check_local_whisper() -> dict[str, Any]:
    base = _setting("LOCAL_WHISPER_BASE_URL", "http://127.0.0.1:8001")
    # faster-whisper HTTP wrappers typically expose /health or /v1/models
    health = await _ping(base, path="/health")
    if health.get("ok"):
        return {"provider": "local_whisper", **health}
    models = await _ping(base, path="/v1/models")
    models["provider"] = "local_whisper"
    models["base_url"] = base
    return models


async def check_ollama() -> dict[str, Any]:
    base = _setting("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    result = await _ping(base, path="/api/tags")
    result["provider"] = "ollama"
    result["base_url"] = base
    result["model"] = _setting("OLLAMA_MODEL", "llama3.1")
    return result


async def check_all() -> dict[str, Any]:
    from app.services import ai_mode, nvidia_nim

    local_whisper = await check_local_whisper()
    ollama = await check_ollama()
    nim = await nvidia_nim.check_nvidia_nim_health()
    return {
        "ai_mode": ai_mode.describe_for_health(),
        "local_whisper": local_whisper,
        "ollama": ollama,
        "nvidia_nim": nim,
    }
