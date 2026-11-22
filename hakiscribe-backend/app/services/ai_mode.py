"""AI operating mode + hybrid per-task routing.

Modes:
  cloud       — current product behaviour (default). Frontier connectors intact.
  hybrid      — explicit per-task mix of cloud + local + private.
  private     — self-hosted / VPC endpoints only (no public SaaS AI).
  local_only  — Compose local ASR/LLM only; fail closed; no cloud AI egress.

Never silently rewrite a frontier selection to local. Optional cross-realm
fallback only when HAKISCRIBE_HYBRID_FALLBACK=explicit_allow and logged by callers.
"""

from __future__ import annotations

import os
from typing import Any, Literal, Optional

AiMode = Literal["cloud", "hybrid", "private", "local_only"]
TaskName = Literal["asr", "detect", "draft", "ask", "research"]

VALID_MODES: tuple[AiMode, ...] = ("cloud", "hybrid", "private", "local_only")
TASKS: tuple[TaskName, ...] = ("asr", "detect", "draft", "ask", "research")

ROUTE_ENV = {
    "asr": "HAKISCRIBE_ROUTE_ASR",
    "detect": "HAKISCRIBE_ROUTE_DETECT",
    "draft": "HAKISCRIBE_ROUTE_DRAFT",
    "ask": "HAKISCRIBE_ROUTE_ASK",
    "research": "HAKISCRIBE_ROUTE_RESEARCH",
}

# Public SaaS / frontier AI providers (blocked in private + local_only).
PUBLIC_CLOUD_PROVIDERS = frozenset(
    {
        "openrouter",
        "openai",
        "anthropic",
        "gemini",
        "gemini_oauth",
        "groq",
        "mistral",
        "nebius",
        "intron",
        "tavily",
        "exa",
        "tavily_exa",
    }
)

PRIVATE_PROVIDERS = frozenset(
    {
        "nvidia_nim",
        "ollama",
        "local_whisper",
        "claude_custom",  # operator-controlled base URL
    }
)

LOCAL_ONLY_PROVIDERS = frozenset({"local_whisper", "ollama"})

LOCAL_ONLY_RESEARCH = frozenset({"off", "local_stub"})

# In-memory overrides from Settings API (demo workspace). Env remains source of truth
# when no override is set.
_runtime_overrides: dict[str, Any] = {}


class AiModeError(RuntimeError):
    """Raised when a provider/task is forbidden for the active mode."""

    def __init__(self, message: str, *, mode: str, task: str, provider: str):
        super().__init__(message)
        self.mode = mode
        self.task = task
        self.provider = provider


def _norm(value: Optional[str], default: str = "") -> str:
    return (value or default).strip().lower()


def get_mode() -> AiMode:
    override = _runtime_overrides.get("mode")
    raw = _norm(override if override is not None else os.environ.get("HAKISCRIBE_AI_MODE"), "cloud")
    if raw not in VALID_MODES:
        return "cloud"
    return raw  # type: ignore[return-value]


def hybrid_fallback_allowed() -> bool:
    return _norm(os.environ.get("HAKISCRIBE_HYBRID_FALLBACK")) == "explicit_allow"


def set_runtime_config(
    *,
    mode: Optional[str] = None,
    routes: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    """Update demo/workspace runtime overrides. Does not write secrets."""
    if mode is not None:
        m = _norm(mode)
        if m not in VALID_MODES:
            raise ValueError(f"Invalid HAKISCRIBE_AI_MODE: {mode}")
        _runtime_overrides["mode"] = m
    if routes:
        stored = dict(_runtime_overrides.get("routes") or {})
        for task, provider in routes.items():
            t = _norm(task)
            if t not in TASKS:
                raise ValueError(f"Unknown task: {task}")
            stored[t] = _norm(provider)
        _runtime_overrides["routes"] = stored
    return snapshot()


def clear_runtime_overrides() -> None:
    _runtime_overrides.clear()


def _default_route(task: TaskName) -> str:
    if task == "asr":
        return _norm(os.environ.get("ASR_PROVIDER"), "openrouter")
    if task == "research":
        return "tavily_exa"
    # Mirror nebius.select_provider precedence without importing (avoid cycles at import).
    env_provider = _norm(os.environ.get("LLM_PROVIDER"))
    if env_provider == "nvidia_nim":
        return "nvidia_nim"
    if os.environ.get("NEBIUS_API_KEY") or _runtime_nebius_hint():
        return "nebius"
    if env_provider:
        return env_provider
    return "openrouter"


def _runtime_nebius_hint() -> bool:
    try:
        from app.services import nebius

        return nebius.is_connected()
    except Exception:  # noqa: BLE001
        return False


def get_route(task: TaskName) -> str:
    mode = get_mode()
    overrides = (_runtime_overrides.get("routes") or {}) if isinstance(_runtime_overrides.get("routes"), dict) else {}
    env_key = ROUTE_ENV[task]
    explicit = _norm(overrides.get(task) or os.environ.get(env_key))

    if mode == "cloud":
        return explicit or _default_route(task)

    if mode == "hybrid":
        return explicit or _default_route(task)

    if mode == "private":
        if explicit:
            return explicit
        if task == "asr":
            return "local_whisper" if _norm(os.environ.get("LOCAL_WHISPER_BASE_URL")) else "nvidia_nim"
        if task == "research":
            return "off"
        return "ollama" if _norm(os.environ.get("OLLAMA_BASE_URL")) else "nvidia_nim"

    # local_only
    if task == "asr":
        return explicit if explicit in LOCAL_ONLY_PROVIDERS else "local_whisper"
    if task == "research":
        return explicit if explicit in LOCAL_ONLY_RESEARCH else "off"
    return explicit if explicit in LOCAL_ONLY_PROVIDERS else "ollama"


def provider_realm(provider: str) -> Literal["public_cloud", "private", "local", "off"]:
    p = _norm(provider)
    if p in ("off", "local_stub"):
        return "off"
    if p in LOCAL_ONLY_PROVIDERS:
        return "local"
    if p in PRIVATE_PROVIDERS:
        return "private"
    if p in PUBLIC_CLOUD_PROVIDERS or p:
        # Unknown connector ids (e.g. user Ask providers) treated as public cloud.
        return "public_cloud"
    return "off"


def is_provider_allowed(task: TaskName, provider: str) -> bool:
    mode = get_mode()
    p = _norm(provider)
    realm = provider_realm(p)

    if mode == "cloud":
        return True

    if mode == "hybrid":
        return True  # any assigned provider allowed; validation is separate

    if mode == "private":
        if task == "research":
            return p in ("off", "local_stub")
        return realm in ("private", "local")

    # local_only
    if task == "research":
        return p in LOCAL_ONLY_RESEARCH
    return p in LOCAL_ONLY_PROVIDERS


def assert_provider_allowed(task: TaskName, provider: str) -> str:
    p = _norm(provider)
    if not is_provider_allowed(task, p):
        mode = get_mode()
        raise AiModeError(
            f"Provider '{p}' is not allowed for task '{task}' in AI mode '{mode}'. "
            f"Switch mode or change HAKISCRIBE_ROUTE_{task.upper()}.",
            mode=mode,
            task=task,
            provider=p,
        )
    return p


def resolve_asr_provider_name() -> str:
    name = get_route("asr")
    return assert_provider_allowed("asr", name)


def resolve_llm_provider(task: TaskName = "detect", explicit: Optional[str] = None) -> str:
    """Resolve LLM backend for detect/draft/ask. Preserves cloud precedence when mode=cloud."""
    mode = get_mode()
    if mode == "cloud":
        if explicit:
            return assert_provider_allowed(task, explicit)
        from app.services import nebius as nebius_service

        # Keep historical select_provider behaviour for cloud.
        return assert_provider_allowed(task, nebius_service.select_provider(explicit))

    if explicit:
        return assert_provider_allowed(task, explicit)

    route_task: TaskName = task if task in ("detect", "draft", "ask") else "detect"
    return assert_provider_allowed(route_task, get_route(route_task))


def resolve_research_route() -> str:
    return assert_provider_allowed("research", get_route("research"))


def prefer_in_process_jobs() -> bool:
    """Trigger.dev is cloud orchestration — prefer in-process under local_only."""
    return get_mode() == "local_only"


def snapshot() -> dict[str, Any]:
    mode = get_mode()
    routes = {task: get_route(task) for task in TASKS}
    allowed = {
        task: is_provider_allowed(task, routes[task]) for task in TASKS
    }
    return {
        "mode": mode,
        "routes": routes,
        "routes_allowed": allowed,
        "hybrid_fallback": hybrid_fallback_allowed(),
        "prefer_in_process_jobs": prefer_in_process_jobs(),
        "frontier_preserved": mode in ("cloud", "hybrid"),
        "runtime_overrides": {
            "mode": _runtime_overrides.get("mode"),
            "routes": dict(_runtime_overrides.get("routes") or {}),
        },
    }


def describe_for_health() -> dict[str, Any]:
    snap = snapshot()
    return {
        "mode": snap["mode"],
        "routes": snap["routes"],
        "routes_allowed": snap["routes_allowed"],
        "hybrid_fallback": snap["hybrid_fallback"],
        "frontier_preserved": snap["frontier_preserved"],
    }
