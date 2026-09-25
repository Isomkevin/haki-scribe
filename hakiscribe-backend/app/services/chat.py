"""Multi-turn chat about one session's verified transcript.

Each call sends the full thread history so the chosen model genuinely
converses. Routing mirrors the Ask task: ``provider:model`` ids go through
the user's own connected key, anything else through OpenRouter.
"""

from __future__ import annotations

import logging
from typing import Optional

import httpx

from app.integrations import llm_client
from app.models.schemas import TranscriptSegment
from app.services import generation, integrations

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are HakiScribe's assistant for a Kenyan legal professional, in an ongoing "
    "conversation about one recorded session. Ground every factual statement in the "
    "verified, non-redacted transcript below. Never invent parties, figures, dates or "
    "authorities; say [NOT ON THE RECORD] when something is not in the transcript. "
    "You may use general legal knowledge to explain, but label it as general guidance. "
    "Be concise, practical and use markdown for lists."
)


class ChatError(Exception):
    pass


def _system(transcript: list[TranscriptSegment]) -> str:
    record = generation.format_transcript(transcript) or "(The transcript is empty so far.)"
    return f"{SYSTEM_PROMPT}\n\nVerified transcript:\n{record}"


async def _openai_compatible(base_url: str, key: str, model: str, system: str, history: list[dict], extra: dict | None = None) -> str:
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json", **(extra or {})}
    async with httpx.AsyncClient(timeout=180) as client:
        resp = await client.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers=headers,
            json={"model": model, "messages": [{"role": "system", "content": system}, *history]},
        )
    if resp.status_code >= 400:
        raise ChatError(f"The model returned {resp.status_code}: {resp.text[:240]}")
    choices = resp.json().get("choices") or []
    return str((choices[0].get("message") or {}).get("content") or "").strip() if choices else ""


async def _anthropic(key: str, model: str, system: str, history: list[dict]) -> str:
    async with httpx.AsyncClient(timeout=180) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": model, "max_tokens": 4096, "system": system, "messages": history},
        )
    if resp.status_code >= 400:
        raise ChatError(f"Claude returned {resp.status_code}: {resp.text[:240]}")
    parts = resp.json().get("content") or []
    return "".join(p.get("text", "") for p in parts if isinstance(p, dict)).strip()


def _gemini_contents(history: list[dict]) -> list[dict]:
    return [
        {"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
        for m in history
    ]


async def _gemini_post(url: str, headers: dict, system: str, history: list[dict]) -> str:
    async with httpx.AsyncClient(timeout=180) as client:
        resp = await client.post(
            url,
            headers={"Content-Type": "application/json", **headers},
            json={"systemInstruction": {"parts": [{"text": system}]}, "contents": _gemini_contents(history)},
        )
    if resp.status_code >= 400:
        raise ChatError(f"Gemini returned {resp.status_code}: {resp.text[:240]}")
    candidates = resp.json().get("candidates") or []
    if not candidates:
        return ""
    parts = (candidates[0].get("content") or {}).get("parts") or []
    return "".join(p.get("text", "") for p in parts).strip()


async def _via_provider(provider_id: str, model: str, system: str, history: list[dict]) -> str:
    creds = await integrations.get_fresh_creds(provider_id)
    if not creds:
        raise ChatError("That connector is no longer connected. Reconnect it under Settings → Connectors.")
    key = str(creds.get("api_key") or "")
    if provider_id == "anthropic":
        return await _anthropic(key, model or "claude-3-5-sonnet-20241022", system, history)
    if provider_id == "openai":
        return await _openai_compatible("https://api.openai.com/v1", key, model or "gpt-4o", system, history)
    if provider_id == "mistral":
        return await _openai_compatible("https://api.mistral.ai/v1", key, model or "mistral-large-latest", system, history)
    if provider_id == "groq":
        return await _openai_compatible("https://api.groq.com/openai/v1", key, model or "llama-3.3-70b-versatile", system, history)
    if provider_id == "openrouter":
        return await _openai_compatible(
            "https://openrouter.ai/api/v1", key, model or creds.get("default_model") or "openai/gpt-4o",
            system, history, integrations.openrouter_headers(),
        )
    if provider_id == "claude_custom":
        return await _openai_compatible(str(creds.get("base_url") or ""), key, model or "gpt-4o", system, history)
    if provider_id == "gemini":
        m = model or "gemini-1.5-flash"
        return await _gemini_post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={key}", {}, system, history
        )
    if provider_id == "gemini_oauth":
        project = str(creds.get("project_id") or "").strip()
        loc = integrations.vertex_location(creds)
        m = model or "gemini-2.0-flash"
        url = (
            f"https://{loc}-aiplatform.googleapis.com/v1/projects/{project}"
            f"/locations/{loc}/publishers/google/models/{m}:generateContent"
        )
        return await _gemini_post(url, {"Authorization": f"Bearer {creds.get('access_token', '')}"}, system, history)
    raise ChatError(f"{provider_id} cannot be used for chat.")


async def reply(model: Optional[str], transcript: list[TranscriptSegment], history: list[dict]) -> str:
    """history: [{role: user|assistant, content}], oldest first, ending with the user turn."""
    system = _system(transcript)
    chosen = (model or "").strip() or llm_client.default_model()
    if ":" in chosen and chosen.split(":", 1)[0] in integrations.provider_ids():
        provider_id, model_name = chosen.split(":", 1)
        text = await _via_provider(provider_id, model_name, system, history)
    elif integrations.get_creds("openrouter"):
        text = await _via_provider("openrouter", chosen, system, history)
    else:
        key = llm_client.api_key()
        if not key:
            raise ChatError("No AI model is configured on the server. Connect one under Settings → Connectors.")
        text = await _openai_compatible(
            "https://openrouter.ai/api/v1", key, chosen, system, history, integrations.openrouter_headers()
        )
    if not text:
        raise ChatError("The model returned an empty reply. Try again or pick another model.")
    return text
