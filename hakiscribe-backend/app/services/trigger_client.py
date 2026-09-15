"""
Thin REST client for Trigger.dev (no JS SDK needed from Python).

Used to run detection and generation as durable, retried background tasks
instead of blocking the request path forever.

Task *code* lives in the repo-root `src/trigger/` TypeScript project.
Those tasks are thin relays into this backend's `/internal/detect` and
`/internal/generate` endpoints.

`trigger_and_wait` returns None if TRIGGER_SECRET_KEY isn't set, which
callers treat as "not configured — fall back to in-process execution."

REST reference:
- Trigger: POST https://api.trigger.dev/api/v1/tasks/{taskIdentifier}/trigger
- Poll:    GET  https://api.trigger.dev/api/v3/runs/{runId}
  (v3 includes status + output, and outputPresignedUrl for large payloads)
- Result:  GET  https://api.trigger.dev/api/v1/runs/{runId}/result
  (kept as a fallback; historically returned 404 even after COMPLETED)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

API_BASE_V1 = "https://api.trigger.dev/api/v1"
API_BASE_V3 = "https://api.trigger.dev/api/v3"

_SUCCESS = {"COMPLETED"}
_FAILURE = {
    "CANCELED",
    "FAILED",
    "CRASHED",
    "SYSTEM_FAILURE",
    "EXPIRED",
    "TIMED_OUT",
    "INTERRUPTED",
}


def _api_key() -> Optional[str]:
    return os.environ.get("TRIGGER_SECRET_KEY") or None


def _parse_output(raw: Any, output_type: Optional[str] = None) -> Any:
    if isinstance(raw, str):
        ctype = (output_type or "application/json").lower()
        if ctype.startswith("application/json") or raw[:1] in {"{", "["}:
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return raw
    return raw


async def _fetch_presigned(client: httpx.AsyncClient, url: str) -> Any:
    resp = await client.get(url)
    resp.raise_for_status()
    try:
        return resp.json()
    except json.JSONDecodeError:
        return _parse_output(resp.text)


async def _output_from_run(client: httpx.AsyncClient, run: dict[str, Any]) -> Any:
    if "output" in run and run["output"] is not None:
        return _parse_output(run["output"], run.get("outputType"))
    presigned = run.get("outputPresignedUrl")
    if presigned:
        return await _fetch_presigned(client, presigned)
    # Fall back to the dedicated result endpoint for older workers.
    run_id = run["id"]
    result_resp = await client.get(f"{API_BASE_V1}/runs/{run_id}/result")
    if result_resp.status_code == 404:
        raise RuntimeError(f"Trigger.dev run {run_id} completed but result is unavailable")
    result_resp.raise_for_status()
    result = result_resp.json()
    if not result.get("ok", False):
        raise RuntimeError(
            f"Trigger.dev task {run.get('taskIdentifier')} (run {run_id}) failed: {result.get('error')}"
        )
    return _parse_output(result.get("output"), result.get("outputType"))


async def trigger_and_wait(
    task_id: str,
    payload: dict[str, Any],
    timeout_s: float = 90.0,
    poll_interval_s: float = 1.5,
) -> Optional[Any]:
    """Returns the task's output on success, raises on task failure or
    timeout, or returns None if Trigger.dev isn't configured (caller's
    signal to fall back to in-process execution)."""
    api_key = _api_key()
    if not api_key:
        return None

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            trigger_resp = await client.post(
                f"{API_BASE_V1}/tasks/{task_id}/trigger",
                headers=headers,
                json={"payload": payload},
            )
            trigger_resp.raise_for_status()
            run_id = trigger_resp.json()["id"]

            elapsed = 0.0
            while elapsed < timeout_s:
                run_resp = await client.get(f"{API_BASE_V3}/runs/{run_id}", headers=headers)
                if run_resp.status_code == 404:
                    await asyncio.sleep(poll_interval_s)
                    elapsed += poll_interval_s
                    continue
                run_resp.raise_for_status()
                run = run_resp.json()
                status = run.get("status") or ""

                if status in _SUCCESS:
                    return await _output_from_run(client, run)

                if status in _FAILURE:
                    err = None
                    for attempt in reversed(run.get("attempts") or []):
                        if attempt.get("error"):
                            err = attempt["error"]
                            break
                    raise RuntimeError(
                        f"Trigger.dev task {task_id} (run {run_id}) ended with {status}: {err}"
                    )

                await asyncio.sleep(poll_interval_s)
                elapsed += poll_interval_s

            raise TimeoutError(
                f"Trigger.dev task {task_id} (run {run_id}) did not finish within {timeout_s}s"
            )
    except Exception as exc:  # noqa: BLE001 — callers fall back to in-process logic
        logger.warning("Trigger.dev %s failed (%s); falling back in-process", task_id, exc)
        return None
