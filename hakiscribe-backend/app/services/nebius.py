"""NVIDIA Nemotron on Nebius Token Factory — HakiScribe's default AI compute.

Everything here is server-side only: the NEBIUS_API_KEY lives in the
connector store (or the workspace env) and never reaches the browser.

Model ids are never hardcoded — they are discovered from
``GET {base}/models`` (10-minute cache) and the Nemotron model whose id
matches the requested tier ("ultra", "super" or "nano") is picked at call
time unless the user set an explicit override on the connector card.

Call contract: :func:`complete` returns ``{"text", "model", "latency_ms", "tier"}``
or raises. Callers must NOT silently fall back to another provider when Nebius
was the selected compute — surface the error so the demo stays honest.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

import httpx

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.tokenfactory.nebius.com/v1"
MODELS_CACHE_TTL_S = 600  # 10 minutes
RETRY_BACKOFF_S = 0.75

# Task → tier. Tray detection and research synthesis run on SUPER,
# document drafting on ULTRA. NANO stays available for cheap utility tasks.
TIER_FOR_TASK = {
    "detection": "super",
    "draft": "ultra",
    "research": "super",
    "calendar": "super",
    "time_entry": "nano",
    "chat": "super",
}

_models_cache: dict[str, Any] = {"base": None, "fetched_at": 0.0, "models": []}
_last_call: Optional[dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Connection + discovery
# ---------------------------------------------------------------------------

def creds() -> dict[str, Any]:
    from app.services import integrations
    return integrations.get_creds("nebius") or {}


def is_connected() -> bool:
    """Connected only when an API key is present (env or connector store)."""
    c = creds()
    return bool(str(c.get("api_key") or "").strip())


def select_provider(explicit: str | None = None) -> str:
    """Resolve which LLM backend to use for detection / drafting.

    Precedence:
    1. Explicit per-call ``provider`` argument.
    2. ``LLM_PROVIDER=nvidia_nim`` — keep the NIM path when someone opted in.
    3. Connected Nebius Token Factory key — wins over a stale
       ``LLM_PROVIDER=openrouter`` on Render so the demo stays eligible.
    4. Any other ``LLM_PROVIDER`` value, else OpenRouter.
    """
    import os

    if explicit:
        return explicit.strip().lower()
    env_provider = os.environ.get("LLM_PROVIDER", "").strip().lower()
    if env_provider == "nvidia_nim":
        return "nvidia_nim"
    if is_connected():
        return "nebius"
    if env_provider:
        return env_provider
    return "openrouter"


def base_url(c: dict[str, Any] | None = None) -> str:
    c = c if c is not None else creds()
    raw = str(c.get("base_url") or "").strip().rstrip("/") or DEFAULT_BASE_URL
    if not re.search(r"/v\d+$", raw):
        raw = f"{raw}/v1"
    return raw


def tier_for_task(task: str) -> str:
    return TIER_FOR_TASK.get(task, "super")


async def list_models(force: bool = False) -> list[str]:
    """Model ids on the Token Factory account, cached for 10 minutes."""
    global _models_cache
    base = base_url()
    now = time.monotonic()
    if (
        not force
        and _models_cache["base"] == base
        and now - float(_models_cache["fetched_at"]) < MODELS_CACHE_TTL_S
        and _models_cache["models"]
    ):
        return list(_models_cache["models"])

    key = str(creds().get("api_key") or "").strip()
    if not key:
        raise RuntimeError("Nebius Token Factory is not connected. Add NEBIUS_API_KEY on the connector card.")
    headers = {"Authorization": f"Bearer {key}"}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{base}/models", headers=headers)
    if resp.status_code in (401, 403):
        raise RuntimeError(f"Nebius rejected the API key ({resp.status_code}). Check NEBIUS_API_KEY on the connector card.")
    if resp.status_code >= 400:
        raise RuntimeError(f"Nebius Token Factory returned {resp.status_code}: {resp.text[:160]}")
    body = resp.json()
    items = body.get("data") or body.get("models") or []
    models = sorted(str(item.get("id") or "") for item in items if isinstance(item, dict) and item.get("id"))
    _models_cache = {"base": base, "fetched_at": now, "models": models}
    return models


def _matches_tier(model_id: str, tier: str) -> bool:
    tail = model_id.rsplit("/", 1)[-1].lower()
    return re.search(rf"(?<![a-z]){tier}(?![a-z])", tail) is not None


async def nemotron_models() -> list[str]:
    models = await list_models()
    return [m for m in models if "nemotron" in m.lower()]


async def resolve_model(tier: str) -> str:
    """The model id for a tier: user override wins, then live discovery."""
    tier = tier.lower()
    c = creds()
    override = str(c.get(f"{tier}_model") or "").strip()
    if not override:
        import os
        override = str(os.environ.get(f"NEMOTRON_{tier.upper()}_MODEL") or "").strip()
    if override:
        return override
    try:
        candidates = await nemotron_models()
    except RuntimeError:
        raise
    tier_matches = [m for m in candidates if _matches_tier(m, tier)]
    if tier_matches:
        return sorted(tier_matches)[-1]
    if candidates:
        raise RuntimeError(
            f"No Nemotron '{tier}' model found on Nebius Token Factory. "
            f"Nemotron models available: {', '.join(candidates)}"
        )
    raise RuntimeError(
        "No Nemotron models found on Nebius Token Factory. "
        "Set the Ultra / Super / Nano model overrides on the connector card, or check the API key."
    )


async def resolve_tiers() -> dict[str, str | None]:
    """Best-effort Ultra/Super/Nano resolution for Test connection / diagnostics."""
    out: dict[str, str | None] = {"ultra": None, "super": None, "nano": None}
    for tier in out:
        try:
            out[tier] = await resolve_model(tier)
        except RuntimeError:
            out[tier] = None
    return out


# ---------------------------------------------------------------------------
# Completion — retry once on 429/5xx with backoff, JSON-mode fallback, repair
# ---------------------------------------------------------------------------

def _clean_text(text: str) -> str:
    """Strip reasoning tags and code fences the model may wrap output in."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = text.replace("</think>", "").strip()
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z0-9_-]*\n?", "", stripped)
        stripped = re.sub(r"\n?```\s*$", "", stripped)
    return stripped.strip()


def _extract_json(text: str) -> str:
    from app.services.tray_logic import extract_json
    try:
        parsed = extract_json(text)
        return json.dumps(parsed)
    except (ValueError, TypeError):
        cleaned = _clean_text(text)
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start >= 0 and end > start:
            return cleaned[start : end + 1]
        return cleaned


def _repair_json(text: str) -> str:
    """One lightweight repair pass: strip fences/think, trim to outermost braces."""
    cleaned = _clean_text(text)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start >= 0 and end > start:
        candidate = cleaned[start : end + 1]
        candidate = re.sub(r",\s*}", "}", candidate)
        candidate = re.sub(r",\s*]", "]", candidate)
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            pass
    start_a, end_a = cleaned.find("["), cleaned.rfind("]")
    if start_a >= 0 and end_a > start_a:
        candidate = cleaned[start_a : end_a + 1]
        candidate = re.sub(r",\s*]", "]", candidate)
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            pass
    return cleaned


async def complete(
    tier: str,
    system_prompt: str,
    user_prompt: str,
    *,
    task: str = "chat",
    json_mode: bool = False,
    timeout_s: float = 120.0,
    privileged_lines_excluded: int = 0,
    session_id: UUID | str | None = None,
) -> dict[str, Any]:
    """One chat completion on Nemotron via Nebius Token Factory.

    Returns {"text", "json_text", "model", "latency_ms", "tier"}; raises
    RuntimeError with a plain-language message. Does not log prompt text.
    """
    global _last_call
    c = creds()
    if not is_connected():
        raise RuntimeError("Nebius Token Factory is not connected.")
    model = await resolve_model(tier)
    base = base_url(c)
    key = str(c.get("api_key") or "").strip()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
    }

    def payload(with_json: bool) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if with_json and json_mode:
            body["response_format"] = {"type": "json_object"}
        return body

    started = time.monotonic()
    status = "ok"
    resolved_model = model
    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            resp = await client.post(f"{base}/chat/completions", headers=headers, json=payload(True))
            # Retry once on rate limiting / server errors with backoff.
            if resp.status_code == 429 or resp.status_code >= 500:
                await asyncio.sleep(RETRY_BACKOFF_S)
                resp = await client.post(f"{base}/chat/completions", headers=headers, json=payload(True))
            # If JSON mode is rejected, retry without it and parse from the text.
            if json_mode and resp.status_code == 400:
                resp = await client.post(f"{base}/chat/completions", headers=headers, json=payload(False))
        latency_ms = int((time.monotonic() - started) * 1000)

        if resp.status_code in (401, 403):
            status = "auth_error"
            raise RuntimeError(f"Nebius rejected the API key ({resp.status_code}). Re-check the key on the connector card.")
        if resp.status_code >= 400:
            status = "http_error"
            raise RuntimeError(f"Nebius Token Factory returned {resp.status_code}: {resp.text[:200]}")

        choices = resp.json().get("choices", [])
        text = ""
        if choices:
            text = str((choices[0].get("message") or {}).get("content") or "")
        if not text:
            status = "empty"
            raise RuntimeError("Nebius Token Factory returned an empty response.")

        returned_model = str(resp.json().get("model") or model)
        cleaned = _clean_text(text)
        json_text = _extract_json(text)
        if json_mode:
            try:
                json.loads(json_text)
            except json.JSONDecodeError:
                json_text = _repair_json(text)
                try:
                    json.loads(json_text)
                except json.JSONDecodeError:
                    status = "json_invalid"
                    # Still return text so callers can attempt their own parse,
                    # but mark the run; do not silently switch providers.
                    pass

        _last_call = {
            "at": datetime.now(timezone.utc).isoformat(),
            "task": task,
            "tier": tier,
            "model": returned_model,
            "latency_ms": latency_ms,
        }
        from app.services import ai_runs, llm_usage
        # Token counts only — never store prompt/response bodies (privilege).
        usage = resp.json().get("usage") or {}
        llm_usage.record(
            task=task,
            model=returned_model,
            provider="nebius",
            prompt="",  # deliberately empty — do not persist transcript
            response="",
            usage=usage,
        )
        ai_runs.record(
            task=task,
            provider="nebius",
            model_id=returned_model,
            latency_ms=latency_ms,
            status=status,
            privileged_lines_excluded=privileged_lines_excluded,
            session_id=session_id,
        )
        return {
            "text": cleaned,
            "json_text": json_text,
            "model": returned_model,
            "latency_ms": latency_ms,
            "tier": tier,
        }
    except Exception:
        latency_ms = int((time.monotonic() - started) * 1000)
        if status == "ok":
            status = "error"
        from app.services import ai_runs
        ai_runs.record(
            task=task,
            provider="nebius",
            model_id=resolved_model,
            latency_ms=latency_ms,
            status=status,
            privileged_lines_excluded=privileged_lines_excluded,
            session_id=session_id,
        )
        raise


def last_call() -> Optional[dict[str, Any]]:
    return dict(_last_call) if _last_call else None


def status() -> dict[str, Any]:
    """Everything the Connectors page 'AI Compute' panel needs."""
    c = creds()
    connected = is_connected()
    from app.services import ai_runs
    return {
        "provider": "NVIDIA Nemotron (Nebius Token Factory)",
        "connected": connected,
        "base_url": base_url(c) if connected else DEFAULT_BASE_URL,
        "tiers": {"tray": "Super", "drafting": "Ultra", "research": "Super"},
        "last_call": last_call() or ai_runs.last_for_provider("nebius"),
    }
