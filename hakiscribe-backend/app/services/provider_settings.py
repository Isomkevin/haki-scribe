"""Demo-mode mirror of provider_settings (no raw API keys).

Production Postgres rows live in migration 002. Demo mode derives the same
shape from the connector store so Connectors + Backend UI share one view.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def list_settings() -> list[dict[str, Any]]:
    from app.services import integrations
    from app.services import nebius

    out: list[dict[str, Any]] = []
    for provider_id in ("nebius", "tavily", "openrouter", "anthropic", "openai", "groq"):
        creds = integrations.get_creds(provider_id) or {}
        if not creds and provider_id not in {"nebius", "tavily"}:
            continue
        enabled = bool(str(creds.get("api_key") or "").strip()) if provider_id != "nebius" else nebius.is_connected()
        if provider_id == "tavily":
            from app.services import tavily
            enabled = tavily.is_configured()
        row: dict[str, Any] = {
            "provider": provider_id,
            "base_url": str(creds.get("base_url") or "").strip() or None,
            "ultra_model": str(creds.get("ultra_model") or "").strip() or None,
            "super_model": str(creds.get("super_model") or "").strip() or None,
            "nano_model": str(creds.get("nano_model") or "").strip() or None,
            "enabled": enabled,
            "default_for_tasks": {},
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if provider_id == "nebius":
            row["default_for_tasks"] = {"tray": "super", "draft": "ultra", "research": "super"}
            row["base_url"] = row["base_url"] or nebius.DEFAULT_BASE_URL
        out.append(row)
    return out


def secrets_status() -> dict[str, str]:
    """set / missing only — never values."""
    import os
    from app.services import integrations

    def _present(provider: str, env: str) -> str:
        creds = integrations.get_creds(provider) or {}
        if str(creds.get("api_key") or "").strip() or str(os.environ.get(env) or "").strip():
            return "set"
        return "missing"

    return {
        "NEBIUS_API_KEY": _present("nebius", "NEBIUS_API_KEY"),
        "TAVILY_API_KEY": _present("tavily", "TAVILY_API_KEY"),
        "OPENROUTER_API_KEY": _present("openrouter", "OPENROUTER_API_KEY"),
        "EXA_API_KEY": "set" if str(os.environ.get("EXA_API_KEY") or "").strip() else "missing",
    }
