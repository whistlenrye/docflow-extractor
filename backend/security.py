"""Upload validation: size cap, magic-byte sniff, filename sanitization."""
from __future__ import annotations
import os
import re
import uuid
from fastapi import HTTPException, UploadFile

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "25")) * 1024 * 1024

# (extension, magic-bytes)
ALLOWED = {
    "pdf":  (b"%PDF",),
    "png":  (b"\x89PNG\r\n\x1a\n",),
    "jpg":  (b"\xff\xd8\xff",),
    "jpeg": (b"\xff\xd8\xff",),
    "webp": (b"RIFF",),  # + "WEBP" at offset 8; checked loosely
}

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_filename(name: str | None) -> str:
    base = os.path.basename(name or "upload")
    base = _SAFE_NAME.sub("_", base).strip("._") or "upload"
    return base[:120]


async def read_limited(file: UploadFile, limit: int = MAX_UPLOAD_BYTES) -> bytes:
    total = 0
    chunks: list[bytes] = []
    while True:
        chunk = await file.read(1024 * 256)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise HTTPException(413, f"File too large (max {limit // (1024*1024)} MB)")
        chunks.append(chunk)
    return b"".join(chunks)


def sniff_type(data: bytes, filename: str) -> str:
    ext = (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()
    if ext not in ALLOWED:
        raise HTTPException(415, f"Unsupported type: {ext or 'unknown'}")
    head = data[:16]
    ok = False
    for sig in ALLOWED[ext]:
        if head.startswith(sig):
            ok = True
            break
    # webp: RIFF....WEBP
    if ext == "webp" and head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        ok = True
    if not ok:
        raise HTTPException(415, "File content does not match its extension")
    return ext


def new_correlation_id() -> str:
    return uuid.uuid4().hex[:12]
