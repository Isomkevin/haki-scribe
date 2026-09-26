"""Small OpenAI-compatible adapter for self-hosted NVIDIA NIM services."""

from __future__ import annotations

import os
from typing import Any

import httpx


def endpoint(value: str | None, path: str) -> str | None:
    """Accept either a NIM base URL or the full OpenAI-compatible route."""
    base = (value or "").strip().rstrip("/")
    if not base:
        return None
    if base.endswith("/v1"):
        return f"{base}{path.removeprefix('/v1')}"
    return base if base.endswith(path) else f"{base}{path}"


def connector_creds() -> dict[str, Any]:
    """Credentials saved on the NVIDIA NIM connector card, when present."""
    try:
        from app.services import integrations

        return integrations.get_creds("nvidia_nim") or {}
    except Exception:  # noqa: BLE001
        return {}


def _setting(field: str, env_name: str) -> str:
    value = str(connector_creds().get(field) or "").strip()
    return value or (os.environ.get(env_name) or "").strip()


def headers() -> dict[str, str]:
    key = _setting("api_key", "NVIDIA_NIM_API_KEY")
    return {"Authorization": f"Bearer {key}"} if key else {}


def asr_endpoint() -> str | None:
    return endpoint(_setting("asr_endpoint", "NVIDIA_NIM_ASR_ENDPOINT"), "/v1/audio/transcriptions")


def llm_endpoint() -> str | None:
    return endpoint(_setting("llm_endpoint", "NVIDIA_NIM_LLM_ENDPOINT"), "/v1/chat/completions")


def llm_model() -> str:
    return _setting("llm_model", "NVIDIA_NIM_LLM_MODEL") or "meta/llama-3.1-8b-instruct"


async def complete(system_prompt: str, user_prompt: str, *, timeout_s: float = 60.0) -> str | None:
    url = llm_endpoint()
    if not url:
        raise RuntimeError("NVIDIA_NIM_LLM_ENDPOINT is not configured")
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        response = await client.post(
            url,
            headers=headers(),
            json={
                "model": llm_model(),
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
        )
        response.raise_for_status()
        body = response.json()
    return (body["choices"][0]["message"]["content"] or "").strip() or None


async def _ping(url: str | None) -> dict[str, Any]:
    if not url:
        return {"configured": False, "ok": False, "status": None}
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(url)
        return {"configured": True, "ok": response.is_success, "status": response.status_code}
    except httpx.HTTPError as exc:
        return {"configured": True, "ok": False, "status": None, "error": str(exc)}


async def check_nvidia_nim_health() -> dict[str, dict[str, Any]]:
    """Ping configured NIM API routes without making either endpoint mandatory."""
    return {"asr": await _ping(asr_endpoint()), "llm": await _ping(llm_endpoint())}
