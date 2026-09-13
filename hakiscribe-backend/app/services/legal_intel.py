"""Ground Exa retrieval in matters and transcripts.

Generic web/news queries are refused. Every search is built from a
session record and/or a persisted matter, then hits are kept only when
they share distinctive terms with that context.
"""

from __future__ import annotations

import os
import re
import uuid
from typing import Any, Optional

from app.integrations import exa_client
from app.models.schemas import Contact, FlaggedMoment, Matter, TranscriptSegment
from app.services import generation, news_store, storage

TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9'’.-]{2,}|clause\s+\d+|section\s+\d+|s\.\s*\d+", re.IGNORECASE)

STOP = {
    "the", "and", "for", "that", "this", "with", "from", "they", "them", "then",
    "have", "has", "had", "was", "were", "are", "been", "being", "will", "would",
    "could", "should", "shall", "into", "onto", "about", "after", "before",
    "their", "there", "these", "those", "what", "when", "where", "which", "who",
    "your", "ours", "also", "just", "than", "then", "very", "more", "some",
    "such", "only", "over", "under", "because", "while", "between", "through",
    "please", "thanks", "thank", "yes", "yeah", "okay", "ok", "well", "like",
    "said", "says", "come", "coming", "want", "wanted", "need", "needed",
    "client", "meeting", "conversation", "session", "speaker", "adv",
    "kenya", "kenyan", "law", "legal", "latest", "news", "update", "updates",
    "hakuna", "kitu", "sasa", "basi", "ndiyo", "sawa",
}

LEGAL_HINTS = {
    "act", "arbitration", "award", "bill", "charge", "clause", "constitution",
    "contract", "contractor", "contractors", "damages", "defective", "demand",
    "employment", "gazette", "hearing", "injunction", "judiciary", "lease",
    "limitation", "notice", "precedent", "privilege", "remedial", "section",
    "statute", "tribunal", "works", "appeal", "plaint", "petition", "slab",
}

WEAK_ALONE = {
    "site", "fact", "start", "take", "happened", "meant", "complete", "coming",
    "going", "asked", "june", "july", "friday", "tuesday", "morning", "letter",
    "payment", "withheld", "deadline", "james", "privileged",
}

LEGAL_SIGNAL = LEGAL_HINTS | {
    "court", "courts", "kenyalaw", "judgement", "judgment", "ruling", "gazette",
    "arbitrator", "advocate", "statute", "cap",
}

GENERIC_URL_TERMS = {"www", "http", "https", "html", "com", "org", "go", "ke"}

AUTHORITY_KINDS = {"statute", "case", "gazette", "act", "section", "judgment", "ruling", "notice"}


def _tokens(text: str) -> list[str]:
    found: list[str] = []
    for raw in TOKEN_RE.findall(text or ""):
        token = raw.strip(".'’").lower()
        if len(token) < 3 or token in STOP or token in GENERIC_URL_TERMS:
            continue
        if token not in found:
            found.append(token)
    return found


def _distinctive(terms: list[str]) -> list[str]:
    return [term for term in terms if term not in STOP and (len(term) >= 4 or term in LEGAL_HINTS or any(ch.isdigit() for ch in term))]


def _parse_uuid(value: str | None) -> Optional[uuid.UUID]:
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None


def _contacts_for(matter: Matter | None, session_id: uuid.UUID | None) -> list[Contact]:
    contacts = storage.list_contacts()
    out: list[Contact] = []
    for contact in contacts:
        if matter and (contact.matter_id == matter.id or contact.id in matter.contact_ids):
            out.append(contact)
        elif session_id and contact.session_id == session_id:
            out.append(contact)
    return out


def resolve_scope(session_id: str | None = None, matter_id: str | None = None) -> Optional[dict[str, Any]]:
    """Build a grounded search scope from a session, a matter, or the library."""
    session_uuid = _parse_uuid(session_id)
    matter_uuid = _parse_uuid(matter_id)
    detail = storage.get_session(session_uuid) if session_uuid else None
    matter = storage.get_matter(matter_uuid) if matter_uuid else None
    matters: list[Matter] = []
    transcript: list[TranscriptSegment] = []
    flags: list[FlaggedMoment] = []
    titles: list[str] = []

    if detail is not None:
        transcript = generation.usable_transcript(detail.transcript)
        flags = list(detail.flagged_moments or [])
        titles.append(detail.title)
        matters.extend(detail.matters or [])
        if matter is None and matters:
            matter = matters[0]

    if matter is not None and matter not in matters:
        matters.append(matter)
        for linked in matter.session_ids:
            linked_detail = storage.get_session(linked)
            if linked_detail is None:
                continue
            transcript.extend(generation.usable_transcript(linked_detail.transcript))
            flags.extend(linked_detail.flagged_moments or [])
            titles.append(linked_detail.title)

    if detail is None and matter is None:
        matters = storage.list_matters()
        if not matters:
            return None
        for item in matters:
            for linked in item.session_ids:
                linked_detail = storage.get_session(linked)
                if linked_detail is None:
                    continue
                transcript.extend(generation.usable_transcript(linked_detail.transcript))
                flags.extend(linked_detail.flagged_moments or [])
                titles.append(linked_detail.title)

    contacts = []
    for item in matters:
        contacts.extend(_contacts_for(item, session_uuid))

    phrases: list[str] = []
    for item in matters:
        phrases.extend([item.matter_name, item.client_name])
    phrases.extend(contact.name for contact in contacts)
    phrases.extend(titles)
    phrases.extend(flag.label or "" for flag in flags)
    phrases.extend(segment.text for segment in transcript[:16])

    terms = _distinctive(_tokens(" ".join(part for part in phrases if part)))
    if not terms:
        return None

    title_terms = _distinctive(_tokens(" ".join(titles)))
    matter_terms = _distinctive(_tokens(" ".join(f"{item.matter_name} {item.client_name}" for item in matters)))
    spoken_all = _distinctive(_tokens(" ".join(segment.text for segment in transcript[:16])))
    spoken_legal = [term for term in spoken_all if term in LEGAL_HINTS]
    spoken_terms = spoken_legal or [term for term in spoken_all if term not in WEAK_ALONE][:8]
    party_terms = _distinctive(_tokens(" ".join(contact.name for contact in contacts)))

    focus: list[str] = []
    for group in (matter_terms, title_terms, spoken_legal, party_terms, spoken_terms):
        for term in group:
            if term not in focus and term not in WEAK_ALONE:
                focus.append(term)
    query = " ".join((focus or terms)[:8])
    if matters:
        query = f"{matters[0].matter_name} {query}".strip()

    return {
        "session_id": str(detail.id) if detail else None,
        "matter_id": str(matters[0].id) if matters else None,
        "matter_name": matters[0].matter_name if matters else None,
        "client_name": matters[0].client_name if matters else None,
        "session_title": detail.title if detail else (titles[0] if titles else None),
        "has_transcript": bool(transcript),
        "terms": terms[:24],
        "matter_terms": matter_terms[:12],
        "spoken_terms": spoken_terms[:12],
        "party_terms": party_terms[:12],
        "query": query[:240],
    }


def _hit_text(hit: dict[str, Any]) -> str:
    kind = hit.get("kind")
    kind_text = kind if isinstance(kind, str) and len(kind) <= 40 else ""
    return " ".join(
        str(part)
        for part in (hit.get("title"), hit.get("extract"), hit.get("citation"), kind_text, hit.get("url"))
        if part
    )


def _authority_kind(kind: Any) -> Optional[str]:
    if not isinstance(kind, str) or len(kind) > 40:
        return None
    value = kind.strip().lower()
    return value if value in AUTHORITY_KINDS else None


def score_hit(hit: dict[str, Any], scope: dict[str, Any]) -> Optional[dict[str, Any]]:
    text_terms = set(_tokens(_hit_text(hit)))
    reasons: list[str] = []
    score = 0
    strong = 0

    for label, key, weight in (
        ("Matter", "matter_terms", 3),
        ("On the record", "spoken_terms", 2),
        ("Party", "party_terms", 2),
    ):
        overlap = [term for term in scope.get(key) or [] if term in text_terms and term not in WEAK_ALONE]
        if overlap:
            reasons.append(f"{label}: {', '.join(overlap[:3])}")
            score += weight
            if any(term in LEGAL_HINTS or key != "spoken_terms" for term in overlap):
                strong += 1

    leftover = [
        term
        for term in (scope.get("terms") or [])
        if term in text_terms and term not in WEAK_ALONE and term in LEGAL_HINTS
    ][:3]
    if leftover and not reasons:
        reasons.append("Connected terms: " + ", ".join(leftover))
        score += 2
        strong += 1

    kind = _authority_kind(hit.get("kind"))
    if kind or hit.get("citation"):
        score += 1
        if kind:
            reasons.append(f"Authority: {kind}")

    legal_signal = bool(text_terms & LEGAL_SIGNAL) or bool(kind) or bool(hit.get("citation"))
    if score < 2 or not reasons or strong < 1 or not legal_signal:
        return None

    connected = dict(hit)
    if kind:
        connected["kind"] = kind
    elif isinstance(hit.get("kind"), str) and len(hit["kind"]) > 40:
        connected["kind"] = None
    connected["relevance"] = score
    connected["connection"] = reasons[:3]
    connected["session_id"] = scope.get("session_id")
    connected["matter_id"] = scope.get("matter_id")
    connected["matter_name"] = scope.get("matter_name")
    return connected


async def retrieve(session_id: str | None = None, matter_id: str | None = None, extra_query: str | None = None) -> dict[str, Any]:
    scope = resolve_scope(session_id, matter_id)
    if scope is None:
        return {
            "grounded": False,
            "query": None,
            "scope": None,
            "hits": [],
            "dropped": 0,
            "configured": exa_client.is_configured(),
            "reason": "Legal search needs a matter or a verified transcript. Open a session or generate a matter first.",
        }

    extra = (extra_query or "").strip()
    extra_terms = _distinctive(_tokens(extra))
    if extra and extra_terms:
        allowed = set(scope["terms"])
        if not any(term in allowed for term in extra_terms):
            return {
                "grounded": False,
                "query": extra,
                "scope": scope,
                "hits": [],
                "dropped": 0,
                "configured": exa_client.is_configured(),
                "reason": "That question is not connected to this matter or transcript, so it was not searched.",
            }
        scope["query"] = f"{scope['query']} {extra}".strip()[:240]

    authorities = await exa_client.search_citations(scope["query"])
    developments = await exa_client.search_legal_developments(scope["query"])
    seen: set[str] = set()
    kept: list[dict[str, Any]] = []
    dropped = 0
    for item in authorities + developments:
        url = item.get("url")
        if not url or url in seen:
            continue
        seen.add(str(url))
        scored = score_hit(item, scope)
        if scored is None:
            dropped += 1
            continue
        kept.append(scored)

    kept.sort(key=lambda item: item.get("relevance") or 0, reverse=True)
    stored = news_store.add_hits(
        kept,
        monitor_id=None,
        topic=scope.get("matter_name") or scope.get("session_title") or "legal-intelligence",
        session_id=scope.get("session_id"),
        matter_id=scope.get("matter_id"),
        matter_name=scope.get("matter_name"),
    )
    return {
        "grounded": True,
        "query": scope["query"],
        "scope": {
            "session_id": scope.get("session_id"),
            "matter_id": scope.get("matter_id"),
            "matter_name": scope.get("matter_name"),
            "client_name": scope.get("client_name"),
            "session_title": scope.get("session_title"),
            "has_transcript": scope.get("has_transcript"),
            "terms": scope.get("terms"),
        },
        "hits": stored or kept,
        "dropped": dropped,
        "configured": exa_client.is_configured(),
        "reason": None,
    }


def monitor_webhook_url() -> Optional[str]:
    configured = os.environ.get("EXA_MONITOR_WEBHOOK_URL", "").strip()
    if configured:
        return configured
    base = (os.environ.get("BACKEND_INTERNAL_URL") or "").rstrip("/")
    return f"{base}/webhooks/exa" if base.startswith("http") else None


def results_from_run(run: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not run:
        return []
    output = run.get("output") if isinstance(run.get("output"), dict) else {}
    for candidate in (output.get("results"), run.get("results")):
        if isinstance(candidate, list):
            return [item for item in candidate if isinstance(item, dict)]
    return []


def scope_from_monitor(
    monitor: dict[str, Any] | None,
    metadata: dict[str, Any] | None = None,
) -> Optional[dict[str, Any]]:
    meta = metadata if isinstance(metadata, dict) else {}
    stored_meta = (monitor or {}).get("metadata")
    if isinstance(stored_meta, dict):
        meta = {**stored_meta, **meta}
    session_id = (monitor or {}).get("session_id") or meta.get("session_id")
    matter_id = (monitor or {}).get("matter_id") or meta.get("matter_id")
    scope = resolve_scope(session_id, matter_id)
    if scope:
        return scope

    terms_raw = meta.get("terms") or (monitor or {}).get("terms") or []
    if isinstance(terms_raw, str):
        terms = [token.strip() for token in terms_raw.split(",") if token.strip()]
    else:
        terms = [str(token) for token in terms_raw if token]
    if not terms and not matter_id and not session_id:
        return None
    matter_name = meta.get("matter_name") or (monitor or {}).get("topic")
    return {
        "session_id": session_id,
        "matter_id": matter_id,
        "matter_name": matter_name,
        "client_name": meta.get("client_name"),
        "session_title": None,
        "has_transcript": False,
        "terms": terms[:24],
        "matter_terms": terms[:12],
        "spoken_terms": [],
        "party_terms": [],
        "query": str(matter_name or " ".join(terms[:8])),
    }


def ingest_monitor_results(
    results: list[dict[str, Any]],
    *,
    monitor: dict[str, Any] | None,
    monitor_id: str | None,
    topic: str,
    metadata: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    scope = scope_from_monitor(monitor, metadata)
    normalised: list[dict[str, Any]] = []
    for item in results:
        highlights = item.get("highlights") or []
        raw = {
            "title": item.get("title"),
            "url": item.get("url"),
            "published": item.get("publishedDate") or item.get("published"),
            "extract": highlights[0] if highlights else item.get("text") or item.get("extract"),
            "citation": item.get("citation"),
            "kind": item.get("kind"),
        }
        scored = score_hit(raw, scope) if scope else None
        if scored:
            normalised.append(scored)
    return news_store.add_hits(
        normalised,
        monitor_id=monitor_id,
        topic=topic,
        session_id=(scope or {}).get("session_id") or (monitor or {}).get("session_id"),
        matter_id=(scope or {}).get("matter_id") or (monitor or {}).get("matter_id"),
        matter_name=(scope or {}).get("matter_name"),
    )


def _merge_hits(primary: list[dict[str, Any]], extra: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = {item.get("url") for item in extra if item.get("url")}
    return extra + [item for item in primary if item.get("url") not in seen]


async def _refresh_monitor_run(record: dict[str, Any], retrieved: dict[str, Any]) -> dict[str, Any]:
    monitor_id = record.get("id")
    if not monitor_id:
        return retrieved
    await exa_client.trigger_monitor(str(monitor_id))
    run = await exa_client.wait_for_latest_run(str(monitor_id))
    extra = ingest_monitor_results(
        results_from_run(run),
        monitor=record,
        monitor_id=str(monitor_id),
        topic=str(record.get("topic") or retrieved.get("query") or "legal-intelligence"),
        metadata=record.get("metadata") if isinstance(record.get("metadata"), dict) else None,
    )
    if extra:
        retrieved = {**retrieved, "hits": _merge_hits(retrieved.get("hits") or [], extra)}
    return retrieved


async def watch(session_id: str | None = None, matter_id: str | None = None, period: str = "1d") -> dict[str, Any]:
    retrieved = await retrieve(session_id=session_id, matter_id=matter_id)
    scope = retrieved.get("scope") or {}
    topic = scope.get("matter_name") or scope.get("session_title") or scope.get("session_id") or ""
    if not retrieved.get("grounded") or not topic:
        return {**retrieved, "monitor": None, "created": False}

    existing = news_store.find_monitor_by_topic(str(topic))
    if existing:
        retrieved = await _refresh_monitor_run(existing, retrieved)
        return {**retrieved, "monitor": {**existing, "webhook_secret": None}, "created": False}

    webhook = monitor_webhook_url()
    metadata = {
        key: value
        for key, value in {
            "session_id": str(scope.get("session_id") or ""),
            "matter_id": str(scope.get("matter_id") or ""),
            "matter_name": str(scope.get("matter_name") or topic),
            "client_name": str(scope.get("client_name") or ""),
            "terms": ",".join(scope.get("terms") or []),
        }.items()
        if value
    }

    remote = None
    if webhook and exa_client.is_configured():
        remote = await exa_client.create_monitor(
            name=f"HakiScribe · {str(topic)[:60]}",
            query=retrieved["query"],
            webhook_url=webhook,
            period=period,
            legal=True,
            metadata=metadata,
        )

    record = {
        "id": (remote or {}).get("id"),
        "topic": topic,
        "session_id": scope.get("session_id"),
        "matter_id": scope.get("matter_id"),
        "period": period,
        "webhook_url": webhook,
        "webhook_secret": (remote or {}).get("webhookSecret") or (remote or {}).get("webhook_secret"),
        "status": "active" if remote and (remote or {}).get("id") else "local-only",
        "terms": scope.get("terms") or [],
        "metadata": metadata,
        "error": None if remote and (remote or {}).get("id") else exa_client.last_error(),
    }
    news_store.upsert_monitor(record)
    if record.get("id"):
        retrieved = await _refresh_monitor_run(record, retrieved)
    return {**retrieved, "monitor": {**record, "webhook_secret": None}, "created": True}
