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


def _model_present(wanted: str, available: list[str]) -> bool:
    """Ollama treats "llama3.1" as "llama3.1:latest"."""
    names = set(available) | {a.removesuffix(":latest") for a in available}
    return wanted in names or f"{wanted}:latest" in names


async def check_ollama(*, deep: bool = False) -> dict[str, Any]:
    base = _setting("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    model = _setting("OLLAMA_MODEL", "llama3.1")
    result: dict[str, Any] = {"provider": "ollama", "base_url": base, "model": model}
    target = f"{base}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(target)
        available = [m.get("name") for m in (resp.json().get("models") or [])] if resp.status_code == 200 else []
        present = _model_present(model, available)
        result.update(
            {
                "configured": True,
                "ok": resp.status_code == 200 and present,
                "reachable": resp.status_code == 200,
                "url": target,
                "status": resp.status_code,
                "models_available": available,
                "model_available": present,
                "detail": "ok" if present else f"model '{model}' not pulled — run: ollama pull {model}",
            }
        )
    except Exception as exc:  # noqa: BLE001
        result.update(
            {"configured": True, "ok": False, "reachable": False, "url": target, "status": None, "detail": str(exc)[:200]}
        )
    if deep and result.get("ok"):
        result["generation"] = await _ollama_generate_probe(base, model)
        result["ok"] = result["generation"]["ok"]
        if not result["ok"]:
            result["detail"] = result["generation"]["detail"]
    return result


async def _ollama_generate_probe(base: str, model: str) -> dict[str, Any]:
    """Generate one token. A listed model can still fail to load (e.g. a broken runner)."""
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(
                f"{base}/api/generate",
                json={"model": model, "prompt": "OK", "stream": False, "options": {"num_predict": 1}},
            )
        if resp.status_code == 200:
            return {"ok": True, "detail": "model loaded and generated"}
        try:
            detail = str(resp.json().get("error") or resp.text)
        except ValueError:
            detail = resp.text
        return {"ok": False, "status": resp.status_code, "detail": detail[:300]}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "detail": str(exc)[:300]}


def validate_routes(snapshot: dict[str, Any], probes: dict[str, Any]) -> list[dict[str, str]]:
    """Warnings for routes that point at a local service that is not ready."""
    warnings: list[dict[str, str]] = []
    probe_for = {"local_whisper": "local_whisper", "ollama": "ollama"}
    for task, provider in (snapshot.get("routes") or {}).items():
        key = probe_for.get(provider)
        if key and not (probes.get(key) or {}).get("ok"):
            warnings.append(
                {
                    "task": task,
                    "provider": provider,
                    "detail": str((probes.get(key) or {}).get("detail") or "not reachable"),
                }
            )
        if not (snapshot.get("routes_allowed") or {}).get(task, True):
            warnings.append({"task": task, "provider": provider, "detail": "route not allowed in current AI mode"})
    return warnings


async def check_all(*, deep: bool = False) -> dict[str, Any]:
    """Shallow by default (fast, for /health). deep=True runs a 1-token generation."""
    from app.services import ai_mode, nvidia_nim

    local_whisper = await check_local_whisper()
    ollama = await check_ollama(deep=deep)
    nim = await nvidia_nim.check_nvidia_nim_health()
    probes = {"local_whisper": local_whisper, "ollama": ollama, "nvidia_nim": nim}
    return {
        "ai_mode": ai_mode.describe_for_health(),
        **probes,
        "route_warnings": validate_routes(ai_mode.snapshot(), probes),
    }
