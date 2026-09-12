"""
Thin REST client for Trigger.dev (v3 REST API — no JS SDK needed from a
Python backend). Used to run detection and generation as durable,
retried background tasks instead of blocking HTTP calls.

The actual task *code* lives in the sibling `trigger/` TypeScript
project (Trigger.dev tasks must be TS/JS, deployed to their platform).
Those tasks are thin relays: they call this backend's `/internal/detect`
and `/internal/generate` endpoints, which hold the real logic
(action_detector.py / action_executor.py) — see trigger/README.md.

`trigger_and_wait` returns None if TRIGGER_SECRET_KEY isn't set, which
callers treat as "not configured — fall back to calling the logic
in-process directly." Same graceful-degradation pattern as every other
sponsor integration here.

REST reference:
- Trigger: POST https://api.trigger.dev/api/v1/tasks/{taskIdentifier}/trigger
- Result:  GET  https://api.trigger.dev/api/v1/runs/{runId}/result  (404 until finished)
"""

import asyncio
import logging
import os
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

API_BASE = "https://api.trigger.dev/api/v1"


def _api_key() -> Optional[str]:
    return os.environ.get("TRIGGER_SECRET_KEY") or None


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
        async with httpx.AsyncClient(timeout=30) as client:
            trigger_resp = await client.post(
                f"{API_BASE}/tasks/{task_id}/trigger", headers=headers, json={"payload": payload}
            )
            trigger_resp.raise_for_status()
            run_id = trigger_resp.json()["id"]

            elapsed = 0.0
            while elapsed < timeout_s:
                result_resp = await client.get(f"{API_BASE}/runs/{run_id}/result", headers=headers)
                if result_resp.status_code == 404:
                    await asyncio.sleep(poll_interval_s)
                    elapsed += poll_interval_s
                    continue
                result_resp.raise_for_status()
                result = result_resp.json()
                if not result.get("ok", False):
                    raise RuntimeError(f"Trigger.dev task {task_id} (run {run_id}) failed: {result.get('error')}")
                return result.get("output")

            raise TimeoutError(f"Trigger.dev task {task_id} (run {run_id}) did not finish within {timeout_s}s")
    except Exception as exc:  # noqa: BLE001 — callers fall back to in-process logic
        logger.warning("Trigger.dev %s failed (%s); falling back in-process", task_id, exc)
        return None
