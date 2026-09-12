"""
One entry point for talking to any chat model through OpenRouter, so a
user can run a free-form instruction against the verified transcript on
Claude, GPT, Gemini or anything else the key has access to.

Returns None when OPENROUTER_API_KEY isn't set — callers surface an
honest "no model configured" message on the card rather than inventing
an answer. Same graceful-degradation pattern as every other integration
in this backend.
"""

from __future__ import annotations

import os
from typing import Optional

import httpx

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODELS_URL = "https://openrouter.ai/api/v1/models"

DEFAULT_MODEL = os.environ.get("ASK_MODEL", "openai/gpt-4o")

# Shown in the model picker. Any OpenRouter model id also works if sent
# explicitly by the client — this is a curated shortlist, not a whitelist.
CURATED_MODELS: list[dict[str, str]] = [
    {"id": "openai/gpt-4o", "label": "GPT-4o (OpenAI)"},
    {"id": "anthropic/claude-3.7-sonnet", "label": "Claude 3.7 Sonnet (Anthropic)"},
    {"id": "anthropic/claude-3.5-haiku", "label": "Claude 3.5 Haiku (Anthropic)"},
    {"id": "google/gemini-2.0-flash-001", "label": "Gemini 2.0 Flash (Google)"},
    {"id": "meta-llama/llama-3.3-70b-instruct", "label": "Llama 3.3 70B (Meta)"},
]


def _api_key() -> Optional[str]:
    return os.environ.get("OPENROUTER_API_KEY") or None


def is_configured() -> bool:
    return bool(_api_key())


def available_models() -> dict[str, object]:
    """What the frontend's model picker renders. No network call — the
    curated list is stable and the picker must work instantly."""
    return {
        "configured": is_configured(),
        "default": DEFAULT_MODEL,
        "models": CURATED_MODELS,
    }


async def complete(
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    timeout_s: float = 120.0,
) -> Optional[str]:
    api_key = _api_key()
    if not api_key:
        return None
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        response = await client.post(
            OPENROUTER_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model or DEFAULT_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return (content or "").strip() or None
