from __future__ import annotations

import hashlib
from collections.abc import Iterable


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_stream(chunks: Iterable[bytes]) -> str:
    h = hashlib.sha256()
    for c in chunks:
        h.update(c)
    return h.hexdigest()


def ext_from_content_type(content_type: str | None) -> str:
    if not content_type:
        return "bin"
    mapping = {
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
        "image/gif": "gif",
        "video/mp4": "mp4",
        "video/quicktime": "mov",
        "video/webm": "webm",
    }
    return mapping.get(content_type.split(";", 1)[0].strip().lower(), "bin")


def asset_key(fingerprint: str, content_type: str | None) -> str:
    return f"assets/{fingerprint[:2]}/{fingerprint}.{ext_from_content_type(content_type)}"
