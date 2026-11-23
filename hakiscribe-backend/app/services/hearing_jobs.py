"""Durable job queue for hearing /process runs.

A /process request inserts a job row; a worker claims it under a lease and
renews the lease with a heartbeat while the pipeline runs. If the worker's
process dies (restart, deploy, crash), the lease lapses and any worker, on
the same server or another, claims the job again, up to MAX_ATTEMPTS.

Storage:
- demo: rows live in hearings._jobs and persist with the hearings snapshot;
- production: public.haki_hearing_jobs (migration 004), claimed with a
  conditional UPDATE so two servers can never both win the same job.

Every backend process runs a worker unless HAKISCRIBE_JOB_WORKER=false. The
Trigger.dev process-hearing relay, when configured, is just another worker:
it claims the same job row through /internal/process-hearing.
"""

from __future__ import annotations

import asyncio
import logging
import os
import socket
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from app.services import hearings

logger = logging.getLogger(__name__)

TABLE = "haki_hearing_jobs"
ACTIVE = ("queued", "running")


class JobConflict(RuntimeError):
    """The hearing already has a queued or running job."""


def _env_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.environ.get(name, "") or default))
    except ValueError:
        return default


def lease_seconds() -> int:
    return _env_int("HAKISCRIBE_JOB_LEASE_S", 120)


def heartbeat_seconds() -> int:
    return max(1, min(_env_int("HAKISCRIBE_JOB_HEARTBEAT_S", 30), lease_seconds() // 3 or 1))


def max_attempts() -> int:
    return _env_int("HAKISCRIBE_JOB_MAX_ATTEMPTS", 3)


def poll_seconds() -> float:
    try:
        return max(0.5, float(os.environ.get("HAKISCRIBE_JOB_POLL_S", "") or 5))
    except ValueError:
        return 5.0


def worker_enabled() -> bool:
    return (os.environ.get("HAKISCRIBE_JOB_WORKER") or "true").strip().lower() not in {"0", "false", "no", "off"}


def production_mode() -> bool:
    return (os.environ.get("HAKISCRIBE_PRODUCTION_AUTH") or "false").strip().lower() in {"1", "true", "yes", "on"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _parse(ts: Any) -> Optional[datetime]:
    if not ts:
        return None
    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    parsed = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def lease_expired(job: dict[str, Any], now: Optional[datetime] = None) -> bool:
    expires = _parse(job.get("lease_expires_at"))
    return expires is None or expires <= (now or _now())


def new_job(
    hearing_id: UUID,
    params: dict[str, Any],
    *,
    organisation_id: Optional[UUID] = None,
    workspace_id: Optional[UUID] = None,
    user_id: Optional[str] = None,
) -> dict[str, Any]:
    now = _iso(_now())
    return {
        "id": str(uuid.uuid4()),
        "hearing_id": str(hearing_id),
        "organisation_id": str(organisation_id) if organisation_id else None,
        "workspace_id": str(workspace_id) if workspace_id else None,
        "user_id": user_id,
        "params": dict(params),
        "status": "queued",
        "attempts": 0,
        "max_attempts": max_attempts(),
        "worker_id": None,
        "lease_expires_at": None,
        "last_error": None,
        "created_at": now,
        "updated_at": now,
    }


class MemoryJobStore:
    """Demo store over hearings._jobs; every write persists the snapshot."""

    def _rows(self) -> dict[str, dict[str, Any]]:
        return hearings._jobs

    def insert(self, job: dict[str, Any]) -> dict[str, Any]:
        # No await between the check and the insert, so this is atomic on the event loop.
        if self.active_for(job["hearing_id"]):
            raise JobConflict("This hearing is already queued or processing")
        self._rows()[job["id"]] = dict(job)
        hearings._save()
        return dict(job)

    def get(self, job_id: str) -> Optional[dict[str, Any]]:
        row = self._rows().get(str(job_id))
        return dict(row) if row else None

    def active_for(self, hearing_id: str) -> Optional[dict[str, Any]]:
        for row in self._rows().values():
            if row["hearing_id"] == str(hearing_id) and row["status"] in ACTIVE:
                return dict(row)
        return None

    def candidates(self, now: datetime, limit: int = 10) -> list[dict[str, Any]]:
        rows = [
            r for r in self._rows().values()
            if r["status"] == "queued" or (r["status"] == "running" and lease_expired(r, now))
        ]
        rows.sort(key=lambda r: r["created_at"])
        return [dict(r) for r in rows[:limit]]

    def claim(self, job: dict[str, Any], worker_id: str, now: datetime) -> Optional[dict[str, Any]]:
        row = self._rows().get(job["id"])
        if not row or row["attempts"] != job["attempts"]:
            return None
        if not (row["status"] == "queued" or (row["status"] == "running" and lease_expired(row, now))):
            return None
        row.update(
            status="running",
            worker_id=worker_id,
            attempts=row["attempts"] + 1,
            lease_expires_at=_iso(now + timedelta(seconds=lease_seconds())),
            updated_at=_iso(now),
        )
        hearings._save()
        return dict(row)

    def give_up(self, job: dict[str, Any], error: str) -> bool:
        row = self._rows().get(job["id"])
        if not row or row["attempts"] != job["attempts"] or row["status"] not in ACTIVE:
            return False
        row.update(status="error", worker_id=None, lease_expires_at=None, last_error=error, updated_at=_iso(_now()))
        hearings._save()
        return True

    def heartbeat(self, job_id: str, worker_id: str) -> bool:
        row = self._rows().get(job_id)
        if not row or row["status"] != "running" or row["worker_id"] != worker_id:
            return False
        now = _now()
        row.update(lease_expires_at=_iso(now + timedelta(seconds=lease_seconds())), updated_at=_iso(now))
        # A lease renewal is not worth a full snapshot write; restore requeues running jobs anyway.
        return True

    def finish(self, job_id: str, worker_id: str, status: str, error: Optional[str] = None) -> bool:
        row = self._rows().get(job_id)
        if not row or row["status"] != "running" or row["worker_id"] != worker_id:
            return False
        row.update(status=status, worker_id=None, lease_expires_at=None, last_error=error, updated_at=_iso(_now()))
        hearings._save()
        return True


class SupabaseJobStore:
    """Production store over public.haki_hearing_jobs (migration 004)."""

    def __init__(self, client: Any):
        self.client = client

    def _table(self):
        return self.client.table(TABLE)

    def insert(self, job: dict[str, Any]) -> dict[str, Any]:
        if self.active_for(job["hearing_id"]):
            raise JobConflict("This hearing is already queued or processing")
        try:
            result = self._table().insert(job).execute()
        except Exception as exc:  # noqa: BLE001 — the partial unique index caught a concurrent enqueue
            if "haki_hearing_jobs_one_active" in str(exc) or "23505" in str(exc):
                raise JobConflict("This hearing is already queued or processing") from exc
            raise
        if not result.data:
            raise RuntimeError("Could not queue the hearing job")
        return result.data[0]

    def get(self, job_id: str) -> Optional[dict[str, Any]]:
        result = self._table().select("*").eq("id", str(job_id)).limit(1).execute()
        return result.data[0] if result.data else None

    def active_for(self, hearing_id: str) -> Optional[dict[str, Any]]:
        result = (
            self._table().select("*").eq("hearing_id", str(hearing_id)).in_("status", list(ACTIVE)).limit(1).execute()
        )
        return result.data[0] if result.data else None

    def candidates(self, now: datetime, limit: int = 10) -> list[dict[str, Any]]:
        queued = self._table().select("*").eq("status", "queued").order("created_at").limit(limit).execute()
        stale = (
            self._table().select("*").eq("status", "running").lt("lease_expires_at", _iso(now))
            .order("created_at").limit(limit).execute()
        )
        rows = list(queued.data or []) + list(stale.data or [])
        rows.sort(key=lambda r: str(r["created_at"]))
        return rows[:limit]

    def claim(self, job: dict[str, Any], worker_id: str, now: datetime) -> Optional[dict[str, Any]]:
        # One UPDATE with the expected attempts count: Postgres re-checks the WHERE
        # clause under the row lock, so exactly one concurrent claimer gets a row back.
        query = (
            self._table()
            .update(
                {
                    "status": "running",
                    "worker_id": worker_id,
                    "attempts": int(job["attempts"]) + 1,
                    "lease_expires_at": _iso(now + timedelta(seconds=lease_seconds())),
                    "updated_at": _iso(now),
                }
            )
            .eq("id", job["id"])
            .eq("attempts", int(job["attempts"]))
        )
        if job["status"] == "queued":
            query = query.eq("status", "queued")
        else:
            query = query.eq("status", "running").lt("lease_expires_at", _iso(now))
        result = query.execute()
        return result.data[0] if result.data else None

    def give_up(self, job: dict[str, Any], error: str) -> bool:
        result = (
            self._table()
            .update({"status": "error", "worker_id": None, "lease_expires_at": None, "last_error": error, "updated_at": _iso(_now())})
            .eq("id", job["id"])
            .eq("attempts", int(job["attempts"]))
            .in_("status", list(ACTIVE))
            .execute()
        )
        return bool(result.data)

    def heartbeat(self, job_id: str, worker_id: str) -> bool:
        now = _now()
        result = (
            self._table()
            .update({"lease_expires_at": _iso(now + timedelta(seconds=lease_seconds())), "updated_at": _iso(now)})
            .eq("id", job_id)
            .eq("worker_id", worker_id)
            .eq("status", "running")
            .execute()
        )
        return bool(result.data)

    def finish(self, job_id: str, worker_id: str, status: str, error: Optional[str] = None) -> bool:
        result = (
            self._table()
            .update({"status": status, "worker_id": None, "lease_expires_at": None, "last_error": error, "updated_at": _iso(_now())})
            .eq("id", job_id)
            .eq("worker_id", worker_id)
            .eq("status", "running")
            .execute()
        )
        return bool(result.data)


def default_store():
    if production_mode():
        from app.services.tenant_context import production_client

        return SupabaseJobStore(production_client())
    return MemoryJobStore()


def _hearing_store(job: dict[str, Any]):
    """The hearings store and session kwargs a job runs against."""
    if job.get("organisation_id"):
        from app.services.production_hearings import ProductionHearingsRepo
        from app.services.tenant_context import production_client

        repo = ProductionHearingsRepo(production_client(), UUID(str(job["organisation_id"])))
        return repo, {"workspace_id": UUID(str(job["workspace_id"])), "user_id": str(job.get("user_id") or "pipeline")}
    return hearings, None


def enqueue(
    hearing_id: UUID,
    params: dict[str, Any],
    *,
    store: Any = None,
    hearing_store: Any = None,
    organisation_id: Optional[UUID] = None,
    workspace_id: Optional[UUID] = None,
    user_id: Optional[str] = None,
) -> dict[str, Any]:
    """Insert a queued job and mirror it onto the hearing's pipeline state."""
    store = store or default_store()
    job = store.insert(
        new_job(hearing_id, params, organisation_id=organisation_id, workspace_id=workspace_id, user_id=user_id)
    )
    (hearing_store or hearings).set_pipeline_state(
        hearing_id, state="queued", step="queued", error=None, job_id=job["id"], attempt=0, queue="hearing_jobs"
    )
    return job


def worker_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:6]}"


def claim_next(wid: str, *, store: Any = None) -> Optional[dict[str, Any]]:
    """Claim the oldest runnable job, retiring jobs that ran out of attempts."""
    store = store or default_store()
    now = _now()
    for job in store.candidates(now):
        limit = int(job.get("max_attempts") or max_attempts())
        if job["status"] == "running" and int(job["attempts"]) >= limit:
            error = f"Gave up after {job['attempts']} attempts: the worker stopped responding (restart or crash)"
            if store.give_up(job, error):
                _mirror(job, state="error", step="failed", error=error)
            continue
        claimed = store.claim(job, wid, now)
        if claimed:
            return claimed
    return None


def claim_job(job_id: str, wid: str, *, store: Any = None) -> Optional[dict[str, Any]]:
    """Claim one specific job (the Trigger.dev relay path)."""
    store = store or default_store()
    job = store.get(job_id)
    if not job:
        return None
    if job["status"] == "queued" or (job["status"] == "running" and lease_expired(job)):
        return store.claim(job, wid, _now())
    return None


def _mirror(job: dict[str, Any], **fields: Any) -> None:
    try:
        hearing_store, _ = _hearing_store(job)
        hearing_store.set_pipeline_state(UUID(str(job["hearing_id"])), **fields)
    except Exception as exc:  # noqa: BLE001 — the job row stays authoritative
        logger.warning("Could not mirror job %s state onto hearing: %s", job.get("id"), exc)


async def _heartbeat(job: dict[str, Any], wid: str, store: Any, work: asyncio.Task, lost: asyncio.Event) -> None:
    while not work.done():
        await asyncio.sleep(heartbeat_seconds())
        if work.done():
            return
        try:
            owned = store.heartbeat(job["id"], wid)
        except Exception as exc:  # noqa: BLE001 — a transient DB error must not kill the run
            logger.warning("Heartbeat for job %s failed: %s", job["id"], exc)
            continue
        if not owned:
            logger.warning("Job %s lease lost; stopping this run so another worker owns it", job["id"])
            lost.set()
            work.cancel()
            return


async def run_job(job: dict[str, Any], wid: str, *, store: Any = None) -> str:
    """Run a claimed job to completion. Returns the job's final status."""
    from app.services import ai_mode, hearing_pipeline

    store = store or default_store()
    hearing_id = UUID(str(job["hearing_id"]))
    hearing_store, session_kwargs = _hearing_store(job)
    params = dict(job.get("params") or {})
    attempt = int(job["attempts"])
    limit = int(job.get("max_attempts") or max_attempts())
    _mirror(job, state="running", step="load", error=None, job_id=job["id"], attempt=attempt)

    work = asyncio.create_task(
        hearing_pipeline.process_hearing(
            hearing_id,
            store=hearing_store,
            create_session_kwargs=session_kwargs,
            use_llm=bool(params.get("use_llm", True)),
            diarize=bool(params.get("diarize", False)),
            language_hint=params.get("language_hint"),
        )
    )
    lost = asyncio.Event()
    beat = asyncio.create_task(_heartbeat(job, wid, store, work, lost))
    try:
        await work
    except asyncio.CancelledError:
        if not lost.is_set():
            raise  # this worker is shutting down; the lease lapses and another claims it
        return "lost"
    except (hearing_pipeline.PipelineError, ai_mode.AiModeError, KeyError) as exc:
        # The hearing or settings are wrong; retrying cannot help.
        store.finish(job["id"], wid, "error", str(exc)[:500])
        return "error"
    except Exception as exc:  # noqa: BLE001 — ASR / LLM / network failure: retry if attempts remain
        message = f"{type(exc).__name__}: {exc}"[:500]
        if attempt < limit:
            store.finish(job["id"], wid, "queued", message)
            _mirror(job, state="queued", step="retry", error=f"Attempt {attempt} of {limit} failed: {message}")
            return "queued"
        store.finish(job["id"], wid, "error", message)
        return "error"
    finally:
        beat.cancel()
    store.finish(job["id"], wid, "done")
    return "done"


async def drain_once(*, store: Any = None) -> Optional[str]:
    """Claim and run one job in this process (used right after an enqueue)."""
    store = store or default_store()
    wid = worker_id()
    job = claim_next(wid, store=store)
    if not job:
        return None
    return await run_job(job, wid, store=store)


_running_worker: Optional["JobWorker"] = None


async def dispatch(job: dict[str, Any], background_tasks: Any) -> Optional[str]:
    """Make sure someone picks the job up. Returns a Trigger.dev run id, if used.

    With this process's worker loop running, it claims the job within
    HAKISCRIBE_JOB_POLL_S. Without one (HAKISCRIBE_JOB_WORKER=false, or no
    lifespan as in tests), the Trigger.dev relay is asked to run it, and if
    that is unavailable this request drains it in-process.
    """
    if _running_worker is not None:
        return None
    from app.services import ai_mode, trigger_client

    if not ai_mode.prefer_in_process_jobs():
        run_id = await trigger_client.trigger_enqueue(
            "process-hearing", {"job_id": job["id"], "hearing_id": job["hearing_id"]}
        )
        if run_id:
            _mirror(job, run_id=run_id, queue="trigger")
            return run_id
    background_tasks.add_task(drain_once)
    return None


class JobWorker:
    """Background loop that keeps claiming jobs for the life of the process."""

    def __init__(self) -> None:
        self.id = worker_id()
        self._task: Optional[asyncio.Task] = None

    def start(self) -> None:
        global _running_worker
        if self._task is None:
            self._task = asyncio.create_task(self._loop())
            _running_worker = self

    async def stop(self) -> None:
        global _running_worker
        if _running_worker is self:
            _running_worker = None
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _loop(self) -> None:
        while True:
            try:
                store = default_store()
                job = claim_next(self.id, store=store)
                if job:
                    await run_job(job, self.id, store=store)
                    continue
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 — keep the worker alive (e.g. DB not configured yet)
                logger.warning("Hearing job worker: %s", exc)
            await asyncio.sleep(poll_seconds())
