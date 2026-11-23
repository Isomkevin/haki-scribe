"""File a reviewed hearing pack into the lawyer's HakiChain WorkSpace.

Phase 1 (contract 2026-11):
  Prefer link_matter → upsert_hearing → finalize_transcript against an existing
  HakiChain workspace (no inventing disconnected hs-… matters when linked).
  Fall back to legacy file_matter / file_document when no HC FK is present.
  Next dates still use file_reminder.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from app.integrations import hakichain_client
from app.models.schemas import Hearing, HearingStatus, Matter
from app.services import hearings as hearings_service
from app.services import storage


class FilingError(RuntimeError):
    pass


def _matter_for(hearing: Hearing, store: Any) -> Matter:
    if not hearing.matter_id:
        raise FilingError("Confirm and link a matter before filing to HakiChain")
    if hasattr(store, "get_matter"):
        matter = store.get_matter(hearing.matter_id)
    else:
        matter = storage.get_matter(hearing.matter_id)
    if not matter:
        raise FilingError("Linked matter was not found")
    return matter


def _transcript_segments(session_id: UUID, store: Any) -> list[Any]:
    if hasattr(store, "get_transcript_segments"):
        return list(store.get_transcript_segments(session_id) or [])
    return list(storage.get_transcript(session_id) or [])


def _segments_payload(session_id: UUID, store: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for seg in _transcript_segments(session_id, store):
        out.append(
            {
                "start_ms": getattr(seg, "start_ms", None),
                "end_ms": getattr(seg, "end_ms", None),
                "speaker": getattr(seg, "speaker", None),
                "text": getattr(seg, "text", "") or "",
                "redacted": bool(getattr(seg, "redacted", False)),
            }
        )
    return out


def _format_transcript(session_id: UUID, store: Any) -> str:
    lines: list[str] = []
    for seg in _transcript_segments(session_id, store):
        if getattr(seg, "redacted", False):
            continue
        stamp = ""
        start_ms = getattr(seg, "start_ms", None)
        if start_ms is not None:
            secs = max(0, int(start_ms) // 1000)
            stamp = f"[{secs // 60:02d}:{secs % 60:02d}] "
        speaker = getattr(seg, "speaker", None)
        speaker_prefix = f"{speaker}: " if speaker else ""
        text = getattr(seg, "text", "") or ""
        lines.append(f"{stamp}{speaker_prefix}{text}".rstrip())
    return "\n".join(lines).strip() or "(No non-privileged transcript segments.)"


def _format_proceedings(hearing: Hearing) -> str:
    meta = hearing.platform_metadata or {}
    proc = meta.get("proceedings") or {}
    rules = list(proc.get("rules") or [])
    llm = proc.get("llm") or {}
    items = list(llm.get("items") or [])
    ungrounded = list(llm.get("ungrounded") or [])

    parts = [
        f"# Hearing proceedings pack — {hearing.title}",
        "",
        "NOTICE: This pack was prepared with HakiScribe assistance after human review.",
        "AI-generated summaries and extracted items are NOT authenticated court orders.",
        "Only quote-grounded items should be treated as candidate directions for advocate review.",
        "",
        f"Source: {hearing.source.value if hasattr(hearing.source, 'value') else hearing.source}",
        f"Case reference: {hearing.case_reference or '—'}",
        f"Hearing id: {hearing.id}",
        f"Session id: {hearing.session_id or '—'}",
        f"Meeting URL: {hearing.meeting_url or '—'}",
        f"Starts at: {hearing.starts_at.isoformat() if hearing.starts_at else '—'}",
        "",
        "## Grounded findings (rules + LLM with transcript quotes)",
    ]

    grounded = [*rules, *items]
    if not grounded:
        parts.append("(None.)")
    for item in grounded:
        kind = item.get("kind") or "item"
        method = item.get("method") or ""
        text = item.get("text") or item.get("purpose") or item.get("name") or ""
        quote = item.get("quote") or ""
        date = item.get("date") or ""
        parts.append(f"- [{kind}/{method}] {text}" + (f" (date: {date})" if date else ""))
        if quote:
            parts.append(f'  Quote: "{quote}"')

    parts.extend(["", "## Ungrounded AI items (do not treat as orders)"])
    if not ungrounded:
        parts.append("(None.)")
    for item in ungrounded:
        reason = item.get("reason") or "not grounded to transcript"
        text = item.get("text") or item.get("purpose") or item.get("kind") or ""
        parts.append(f"- {text} — {reason}")

    return "\n".join(parts)


def _next_dates(hearing: Hearing) -> list[dict[str, str]]:
    meta = hearing.platform_metadata or {}
    proc = meta.get("proceedings") or {}
    rules = list(proc.get("rules") or [])
    items = list((proc.get("llm") or {}).get("items") or [])
    out: list[dict[str, str]] = []
    for item in [*rules, *items]:
        kind = str(item.get("kind") or "")
        date = str(item.get("date") or "").strip()
        if kind not in ("next_date", "mention", "hearing") and not date:
            continue
        if not date:
            continue
        title = str(item.get("purpose") or item.get("text") or f"Next date — {hearing.title}")
        out.append(
            {
                "title": title[:160],
                "start": date,
                "description": str(item.get("quote") or item.get("text") or ""),
            }
        )
    return out


def _proceedings_dict(hearing: Hearing) -> dict[str, Any]:
    return dict((hearing.platform_metadata or {}).get("proceedings") or {})


async def file_hearing_pack(
    hearing_id: UUID,
    *,
    actor: str = "workspace",
    store: Any = None,
) -> dict[str, Any]:
    store = store or hearings_service
    hearing = store.get_hearing(hearing_id)
    if hearing is None:
        raise FilingError("Hearing not found")
    if hearing.status not in (HearingStatus.reviewed, HearingStatus.filed):
        raise FilingError("Mark the hearing reviewed before filing to HakiChain")
    if hearing.session_id is None:
        raise FilingError("Hearing has no linked session transcript")

    if not hakichain_client.configured():
        raise FilingError(
            "HakiChain is not connected. Link a hkc_… token under Settings → Connectors → HakiChain."
        )

    matter = _matter_for(hearing, store)
    session_id = str(hearing.session_id)
    results: dict[str, Any] = {
        "hearing_id": str(hearing_id),
        "filed_at": datetime.utcnow().isoformat(),
        "actor": actor,
        "contract_version": hakichain_client.CONTRACT_VERSION,
        "steps": {},
        "errors": [],
    }

    hc_workspace_id = getattr(matter, "hakichain_workspace_id", None)
    hc_client_id = getattr(matter, "hakichain_client_id", None)
    client_id_hint = hc_client_id or f"hs-{matter.id}"

    # Prefer binding to an existing HakiChain workspace when FKs are present.
    if hc_workspace_id or hc_client_id:
        linked = await hakichain_client.link_matter(
            action_key=f"link:{matter.id}",
            workspace_id=hc_workspace_id,
            client_id=hc_client_id,
            scribe_matter_id=str(matter.id),
        )
        if linked:
            results["steps"]["link_matter"] = {
                "ok": True,
                "client_id": linked.get("client_id"),
                "workspace_id": linked.get("workspace_id"),
                "workspace_url": linked.get("workspace_url")
                or hakichain_client.workspace_url(linked.get("client_id")),
                "reused": linked.get("reused"),
            }
            client_id_hint = str(linked.get("client_id") or client_id_hint)
            hc_workspace_id = str(linked.get("workspace_id") or hc_workspace_id or "")
            if hasattr(storage, "link_hakichain_matter") and matter.id:
                storage.link_hakichain_matter(
                    matter.id,
                    hakichain_client_id=client_id_hint,
                    hakichain_workspace_id=hc_workspace_id,
                )
        else:
            results["errors"].append(f"link_matter: {hakichain_client.last_error() or 'failed'}")
            results["steps"]["link_matter"] = {"ok": False, "error": hakichain_client.last_error()}
    else:
        # Legacy invent path when the local matter was never linked to HakiChain.
        matter_filed = await hakichain_client.file_matter(
            action_key=f"hearing-matter:{hearing_id}",
            scribe_matter_id=str(matter.id),
            matter_name=matter.matter_name,
            client_name=matter.client_name,
            session_id=session_id,
        )
        if matter_filed:
            results["steps"]["matter"] = {
                "ok": True,
                "client_id": matter_filed.get("client_id"),
                "workspace_url": matter_filed.get("workspace_url")
                or hakichain_client.workspace_url(matter_filed.get("client_id")),
            }
            client_id_hint = str(matter_filed.get("client_id") or client_id_hint)
            hc_workspace_id = str(matter_filed.get("workspace_id") or "")
        else:
            results["errors"].append(f"file_matter: {hakichain_client.last_error() or 'failed'}")
            results["steps"]["matter"] = {"ok": False, "error": hakichain_client.last_error()}

    # First-class hearing row on HakiChain.
    upserted = await hakichain_client.upsert_hearing(
        scribe_hearing_id=str(hearing_id),
        workspace_id=hc_workspace_id,
        client_id=client_id_hint,
        title=hearing.title,
        status="filed" if hearing.status == HearingStatus.filed else "reviewed",
        case_reference=hearing.case_reference,
        starts_at=hearing.starts_at.isoformat() if hearing.starts_at else None,
        meeting_url=hearing.meeting_url,
        metadata={"source": getattr(hearing.source, "value", str(hearing.source))},
    )
    if upserted:
        results["steps"]["upsert_hearing"] = {
            "ok": True,
            "hearing_id": upserted.get("hearing_id"),
            "workspace_url": upserted.get("workspace_url")
            or hakichain_client.workspace_url(upserted.get("client_id")),
        }
        client_id_hint = str(upserted.get("client_id") or client_id_hint)
        hc_workspace_id = str(upserted.get("workspace_id") or hc_workspace_id or "")
    else:
        # Older ingress without upsert_hearing — continue with document path.
        err = hakichain_client.last_error() or "upsert_hearing unavailable"
        results["steps"]["upsert_hearing"] = {"ok": False, "error": err}
        results["errors"].append(f"upsert_hearing: {err}")

    finalized = await hakichain_client.finalize_transcript(
        action_key=f"hearing-finalize:{hearing_id}",
        scribe_hearing_id=str(hearing_id),
        workspace_id=hc_workspace_id,
        client_id=client_id_hint,
        segments=_segments_payload(hearing.session_id, store),
        proceedings=_proceedings_dict(hearing),
        title=hearing.title,
    )
    if finalized:
        results["steps"]["finalize_transcript"] = {
            "ok": True,
            "hearing_id": finalized.get("hearing_id"),
            "transcript_doc_id": finalized.get("transcript_doc_id"),
            "proceedings_doc_id": finalized.get("proceedings_doc_id"),
            "workspace_url": finalized.get("workspace_url")
            or hakichain_client.workspace_url(finalized.get("client_id")),
            "client_id": finalized.get("client_id"),
        }
        client_id_hint = str(finalized.get("client_id") or client_id_hint)
    else:
        # Fallback: legacy dual file_document when finalize_transcript is not deployed yet.
        err = hakichain_client.last_error() or "finalize_transcript unavailable"
        results["steps"]["finalize_transcript"] = {"ok": False, "error": err}
        results["errors"].append(f"finalize_transcript: {err}")

        transcript_text = _format_transcript(hearing.session_id, store)
        transcript_filed = await hakichain_client.file_document(
            action_key=f"hearing-transcript:{hearing_id}",
            session_id=session_id,
            title=f"Hearing transcript — {hearing.title}",
            document_text=transcript_text,
            client_id=client_id_hint,
            matter_name=matter.matter_name,
            client_name=matter.client_name,
        )
        if transcript_filed:
            results["steps"]["transcript"] = {
                "ok": True,
                "workspace_url": transcript_filed.get("workspace_url")
                or hakichain_client.workspace_url(transcript_filed.get("client_id")),
                "client_id": transcript_filed.get("client_id"),
            }
            client_id_hint = str(transcript_filed.get("client_id") or client_id_hint)
        else:
            results["errors"].append(
                f"file_document(transcript): {hakichain_client.last_error() or 'failed'}"
            )
            results["steps"]["transcript"] = {"ok": False, "error": hakichain_client.last_error()}

        proceedings_text = _format_proceedings(hearing)
        proceedings_filed = await hakichain_client.file_document(
            action_key=f"hearing-proceedings:{hearing_id}",
            session_id=session_id,
            title=f"Hearing proceedings pack — {hearing.title}",
            document_text=proceedings_text,
            client_id=client_id_hint,
            matter_name=matter.matter_name,
            client_name=matter.client_name,
        )
        if proceedings_filed:
            results["steps"]["proceedings"] = {
                "ok": True,
                "workspace_url": proceedings_filed.get("workspace_url")
                or hakichain_client.workspace_url(proceedings_filed.get("client_id")),
                "client_id": proceedings_filed.get("client_id"),
            }
            client_id_hint = str(proceedings_filed.get("client_id") or client_id_hint)
        else:
            results["errors"].append(
                f"file_document(proceedings): {hakichain_client.last_error() or 'failed'}"
            )
            results["steps"]["proceedings"] = {"ok": False, "error": hakichain_client.last_error()}

    reminders: list[dict[str, Any]] = []
    for idx, date_item in enumerate(_next_dates(hearing)):
        filed = await hakichain_client.file_reminder(
            action_key=f"hearing-date:{hearing_id}:{idx}",
            session_id=session_id,
            title=date_item["title"],
            start=date_item["start"],
            description=date_item.get("description") or "",
            client_id=client_id_hint,
            matter_name=matter.matter_name,
            client_name=matter.client_name,
            reminder_type="court-date",
        )
        if filed:
            reminders.append(
                {
                    "ok": True,
                    "title": date_item["title"],
                    "start": date_item["start"],
                    "workspace_url": filed.get("workspace_url")
                    or hakichain_client.workspace_url(filed.get("client_id")),
                }
            )
        else:
            err = hakichain_client.last_error() or "failed"
            reminders.append({"ok": False, "title": date_item["title"], "error": err})
            results["errors"].append(f"file_reminder[{idx}]: {err}")
    results["steps"]["reminders"] = reminders

    workspace_url: Optional[str] = None
    for step in ("finalize_transcript", "upsert_hearing", "link_matter", "proceedings", "transcript", "matter"):
        info = results["steps"].get(step) or {}
        if info.get("workspace_url"):
            workspace_url = info["workspace_url"]
            break
    results["workspace_url"] = workspace_url
    results["client_id"] = client_id_hint
    results["workspace_id"] = hc_workspace_id
    results["ok"] = bool(
        (results["steps"].get("finalize_transcript") or {}).get("ok")
        or (results["steps"].get("transcript") or {}).get("ok")
        or (results["steps"].get("proceedings") or {}).get("ok")
    )

    if not results["ok"]:
        raise FilingError(
            "HakiChain filing failed: " + ("; ".join(results["errors"]) or "no documents accepted")
        )

    if hasattr(store, "mark_filed"):
        hearing = store.mark_filed(hearing_id, filing=results, actor=actor)
    else:
        hearing = hearings_service.mark_filed(hearing_id, filing=results, actor=actor)
    results["hearing"] = hearing
    return results
