"""Durable storage for hearing recordings.

Bytes always land on a local volume (`HAKISCRIBE_RECORDINGS_DIR`, default
`data/recordings`, gitignored) so local_only deployments never need S3. When
S3 is configured (see object_store) the same key is mirrored there too.

Keys are built server-side from the hearing id plus a sanitised filename, so a
client-supplied name can never escape the recordings directory.
"""

from __future__ import annotations

import os
import re
import uuid
from pathlib import Path
from typing import Optional

from app.services import object_store

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


class RecordingTooLarge(ValueError):
    pass


def root() -> Path:
    return Path(os.environ.get("HAKISCRIBE_RECORDINGS_DIR", "data/recordings")).resolve()


def max_bytes() -> int:
    return int(os.environ.get("HAKISCRIBE_MAX_RECORDING_MB", "1024")) * 1024 * 1024


def safe_filename(name: Optional[str], default: str = "recording.bin") -> str:
    base = os.path.basename((name or "").replace("\\", "/")).strip()
    base = _SAFE_NAME.sub("_", base).strip("._")
    return base[:120] or default


def key_for(hearing_id: uuid.UUID, filename: Optional[str]) -> str:
    return f"hearings/{hearing_id}/{safe_filename(filename)}"


def _path_for(key: str) -> Path:
    path = (root() / key).resolve()
    if root() not in path.parents:
        raise ValueError(f"recording key escapes storage root: {key}")
    return path


def save(hearing_id: uuid.UUID, filename: Optional[str], data: bytes, content_type: str = "application/octet-stream") -> dict:
    if len(data) > max_bytes():
        raise RecordingTooLarge(f"recording is {len(data)} bytes; limit is {max_bytes()}")
    key = key_for(hearing_id, filename)
    path = _path_for(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    mirrored = object_store.put_bytes(key, data, content_type=content_type)
    return {"key": key, "bytes": len(data), "content_type": content_type, "s3": mirrored}


def load(key: str) -> Optional[bytes]:
    path = _path_for(key)
    if path.is_file():
        return path.read_bytes()
    return object_store.get_bytes(key)
