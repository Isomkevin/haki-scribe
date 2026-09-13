"""
Optional S3 archive for generated legal documents.

Set S3_BUCKET plus the usual AWS credentials (AWS_ACCESS_KEY_ID,
AWS_SECRET_ACCESS_KEY, AWS_REGION) and every drafted document is written to
the bucket as well as the database, so the firm keeps its own durable copy of
the artifact outside this service. Unset, every function here no-ops.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_state: dict = {"client": None, "checked": False}


def bucket() -> str:
    return os.environ.get("S3_BUCKET", "").strip()


def configured() -> bool:
    return bool(bucket() and os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY"))


def _client():
    if _state["checked"]:
        return _state["client"]
    _state["checked"] = True
    if not configured():
        return None
    try:
        import boto3

        _state["client"] = boto3.client(
            "s3",
            region_name=os.environ.get("AWS_REGION", "eu-west-1"),
            endpoint_url=os.environ.get("S3_ENDPOINT_URL") or None,
        )
    except Exception as exc:  # noqa: BLE001 — archiving must never break generation
        logger.warning("S3 archive unavailable: %s", exc)
        _state["client"] = None
    return _state["client"]


def archive_document(key: str, text: str, content_type: str = "text/plain; charset=utf-8") -> Optional[str]:
    """Store a document and return a time-limited link, or None when unconfigured."""
    client = _client()
    if client is None:
        return None
    try:
        client.put_object(Bucket=bucket(), Key=key, Body=text.encode("utf-8"), ContentType=content_type)
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket(), "Key": key},
            ExpiresIn=int(os.environ.get("S3_LINK_TTL_SECONDS", "604800")),
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not archive document %s to S3: %s", key, exc)
        return None


def status() -> dict:
    return {"configured": configured(), "bucket": bucket() or None}
