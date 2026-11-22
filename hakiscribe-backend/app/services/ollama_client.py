"""OpenAI-compatible chat client for local Ollama (additive; never replaces frontier)."""

from __future__ import annotations

import os
from typing import Any, Optional

import httpx


def base_url() -> str:
    return (os.environ.get("OLLAMA_BASE_URL") or "http://127.0.0.1:11434").strip().rstrip("/")


def default_model() -> str:
    return (os.environ.get("OLLAMA_MODEL") or "llama3.1").strip() or "llama3.1"


def request_timeout_s() -> float:
    """Local CPU inference is slow; a 3B model can need minutes for a long transcript."""
    try:
        return float(os.environ.get("OLLAMA_TIMEOUT_S") or 600)
    except ValueError:
        return 600.0


def configured() -> bool:
    return bool((os.environ.get("OLLAMA_BASE_URL") or "").strip())


async def complete(
    system_prompt: str,
    user_prompt: str,
    *,
    model: Optional[str] = None,
    task: str = "generation",
    timeout_s: Optional[float] = None,
    json_mode: bool = False,
) -> dict[str, Any]:
    """Return {text, model, provider} or raise.

    json_mode makes Ollama constrain output to a valid JSON object, which small
    local models otherwise break often enough to fail whole requests.
    """
    from app.services import ai_mode

    ai_mode.assert_provider_allowed(
        "draft" if task in ("draft", "generation", "calendar", "time_entry") else "detect",
        "ollama",
    )
    url = f"{base_url()}/v1/chat/completions"
    mid = model or default_model()
    payload: dict[str, Any] = {
        "model": mid,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    async with httpx.AsyncClient(timeout=timeout_s if timeout_s is not None else request_timeout_s()) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        body = resp.json()
    text = ((body.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    text = str(text).strip()
    try:
        from app.services import llm_usage

        llm_usage.record(
            task=task,
            model=mid,
            provider="ollama",
            prompt=user_prompt,
            response=text,
            usage=body.get("usage"),
        )
    except Exception:  # noqa: BLE001
        pass
    return {"text": text, "model": mid, "provider": "ollama", "raw": body}
