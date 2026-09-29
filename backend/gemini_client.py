"""Gemini structured-output client. Free-tier model, no persistence of docs."""
from __future__ import annotations
import os
import logging
from google import genai
from google.genai import types
from schemas import ExtractionResult

log = logging.getLogger("docflow.gemini")

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
_client: genai.Client | None = None


def _client_get() -> genai.Client:
    global _client
    if _client is None:
        key = os.getenv("GEMINI_API_KEY", "")
        if not key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        _client = genai.Client(api_key=key)
    return _client


SYSTEM_PROMPT = """You are a precise document-data extraction engine.
Return ONLY the fields present in the document. If a field is absent, set it null.
Never invent values. Set confidence between 0 and 1 based on how clearly the
fields are stated. For line items, capture every row. Currency codes as ISO 4217.
"""


def extract_with_gemini(text: str, doc_type: str, file_bytes: bytes | None,
                        mime: str | None) -> ExtractionResult:
    client = _client_get()
    parts: list[types.Part] = []
    if file_bytes and mime:
        parts.append(types.Part.from_bytes(data=file_bytes, mime_type=mime))
    parts.append(types.Part.from_text(
        text=f"Document type hint: {doc_type}\n\nExtract all structured fields."
        + (f"\n\nOCR/text layer:\n{text[:12000]}" if text else "")
    ))

    resp = client.models.generate_content(
        model=MODEL,
        contents=parts,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_json_schema=ExtractionResult.model_json_schema(),
            temperature=0.0,
        ),
    )
    try:
        result = ExtractionResult.model_validate_json(resp.text or "{}")
    except Exception as e:
        log.warning("schema validation failed: %s", e)
        result = ExtractionResult(
            doc_type=doc_type, confidence=0.0,
            warnings=["Model output failed schema validation; returned empty."],
            model_used=MODEL,
        )
    result.model_used = MODEL
    # truncate raw_text to limit exfil surface
    if result.raw_text and len(result.raw_text) > 2000:
        result.raw_text = result.raw_text[:2000] + "…"
    return result
