"""
One entry point for talking to any chat model through OpenRouter, so a
user can run a free-form instruction against the verified transcript on
Claude, GPT, Gemini or anything else the key has access to.

The key comes from the OpenRouter connector when connected, otherwise
OPENROUTER_API_KEY. Returns None when neither is set — callers surface
an honest "no model configured" message on the card rather than inventing
an answer.
"""

from __future__ import annotations

import os
from typing import Optional

import httpx

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODELS_URL = "https://openrouter.ai/api/v1/models"

# Shown in the model picker. Any OpenRouter model id also works if sent
# explicitly by the client — this is a curated shortlist, not a whitelist.
CURATED_MODELS: list[dict[str, str]] = [
    {"id": "openai/gpt-4o", "label": "GPT-4o (OpenAI)"},
    {"id": "anthropic/claude-3.7-sonnet", "label": "Claude 3.7 Sonnet (Anthropic)"},
    {"id": "anthropic/claude-3.5-haiku", "label": "Claude 3.5 Haiku (Anthropic)"},
    {"id": "google/gemini-2.0-flash-001", "label": "Gemini 2.0 Flash (Google)"},
    {"id": "meta-llama/llama-3.3-70b-instruct", "label": "Llama 3.3 70B (Meta)"},
]


def api_key() -> Optional[str]:
    from app.services import integrations

    creds = integrations.get_creds("openrouter") or {}
    key = str(creds.get("api_key") or "").strip()
    return key or os.environ.get("OPENROUTER_API_KEY") or None


def default_model() -> str:
    from app.services import integrations

    creds = integrations.get_creds("openrouter") or {}
    return str(creds.get("default_model") or os.environ.get("ASK_MODEL") or "openai/gpt-4o").strip()


DEFAULT_MODEL = os.environ.get("ASK_MODEL", "openai/gpt-4o")


def _api_key() -> Optional[str]:
    return api_key()


def is_configured() -> bool:
    return bool(api_key())


def available_models() -> dict[str, object]:
    """What the frontend's model picker renders. No network call — the
    curated list is stable and the picker must work instantly."""
    return {
        "configured": is_configured(),
        "default": default_model(),
        "models": CURATED_MODELS,
    }


def _headers(api_key_value: str) -> dict[str, str]:
    from app.services.integrations import openrouter_headers

    return {
        "Authorization": f"Bearer {api_key_value}",
        **openrouter_headers(),
    }


async def complete(
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    timeout_s: float = 120.0,
) -> Optional[str]:
    key = api_key()
    if not key:
        return None
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        response = await client.post(
            OPENROUTER_URL,
            headers=_headers(key),
            json={
                "model": model or default_model(),
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return (content or "").strip() or None
