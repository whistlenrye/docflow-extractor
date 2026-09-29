from __future__ import annotations

import io
import logging
import os
import secrets
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from extractors import get_extractor
from form_filler import fill_form, result_to_fields
from gemini_client import extract_with_gemini, gemini_configured
from parser import merge_extractions, parse_document
from schemas import DocumentType, ExtractionResult, LineItem
from security import MAX_TEXT_CHARS, new_correlation_id, read_limited, sanitize_filename, sniff_type

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("docflow")

limiter = Limiter(key_func=get_remote_address, default_limits=[
    f"{os.getenv('RATE_LIMIT_PER_MIN', '30')}/minute"
])


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info(
        "DocFlow backend starting; gemini_configured=%s model=%s",
        gemini_configured(),
        os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
    )
    yield


app = FastAPI(title="DocFlow Extractor", version="1.1.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_cors = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

MIME = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "txt": "text/plain",
    "csv": "text/plain",
    "md": "text/plain",
}


def _require_api_key(request: Request) -> None:
    expected = os.getenv("EXTRACT_API_KEY", "").strip()
    if not expected:
        return
    got = request.headers.get("x-api-key", "")
    if not secrets.compare_digest(got, expected):
        raise HTTPException(401, "invalid api key")


def text_from_upload(data: bytes, ext: str) -> str:
    if ext in {"txt", "csv", "md"}:
        return data.decode("utf-8-sig", errors="replace")
    if ext != "pdf":
        return ""
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            parts: list[str] = []
            for page in pdf.pages[:30]:
                parts.append(page.extract_text() or "")
            return "\n".join(parts)
    except Exception:
        log.warning("pdf text extraction failed")
        return ""


@app.get("/health")
def health():
    return {
        "status": "ok",
        "gemini_configured": gemini_configured(),
        "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        "parser": "deterministic",
    }


@app.post("/extract", response_model=ExtractionResult)
@limiter.limit(f"{os.getenv('RATE_LIMIT_PER_MIN', '30')}/minute")
async def extract(
    request: Request,
    file: UploadFile | None = File(None),
    text: str | None = Form(None),
    doc_type: str | None = Form(None),
):
    cid = new_correlation_id()
    try:
        _require_api_key(request)
        detected = doc_type or "generic.invoice"
        if detected not in DocumentType.__args__:  # type: ignore[attr-defined]
            raise HTTPException(400, f"Unknown doc_type: {detected}")

        raw: bytes | None = None
        mime: str | None = None
        layer = ""
        if file is not None and file.filename:
            raw = await read_limited(file)
            fname = sanitize_filename(file.filename)
            ext = sniff_type(raw, fname)
            mime = MIME[ext]
            layer = text_from_upload(raw, ext)
        pasted = (text or "").strip()
        if pasted and len(pasted) > MAX_TEXT_CHARS:
            raise HTTPException(413, "Pasted text is too long")
        if not layer and pasted:
            layer = pasted
        elif layer and pasted:
            layer = f"{layer}\n\n{pasted}"
        if raw is None and not layer:
            raise HTTPException(400, "Provide a file or pasted text")

        parsed = get_extractor(detected).extract(layer, detected)
        result = parsed
        if gemini_configured():
            try:
                model = extract_with_gemini(layer, detected, raw, mime)
                result = merge_extractions(model, parsed)
            except Exception as exc:
                log.warning("[%s] gemini failed, using parser: %s", cid, type(exc).__name__)
                result = parsed
                result.warnings = list(dict.fromkeys([
                    *result.warnings,
                    f"Gemini unavailable ({type(exc).__name__}); deterministic parser used.",
                ]))
        else:
            result.warnings = list(dict.fromkeys([
                *result.warnings,
                "GEMINI_API_KEY is not set; deterministic parser used.",
            ]))

        if layer:
            result.raw_text = layer[:2000]
        elif result.raw_text:
            result.raw_text = result.raw_text[:2000]
        return result
    except HTTPException:
        raise
    except Exception:
        log.exception("[%s] unhandled", cid)
        return JSONResponse(
            status_code=500,
            content={"detail": "extraction failed", "cid": cid},
        )


class FillRequest(ExtractionResult):
    """Same shape /extract returns, plus where to send it."""
    target_url: str | None = None
    dry_run: bool = False


@app.post("/fill")
@limiter.limit(f"{os.getenv('RATE_LIMIT_PER_MIN', '30')}/minute")
async def fill(request: Request, body: FillRequest):
    cid = new_correlation_id()
    try:
        _require_api_key(request)
        result = ExtractionResult.model_validate(body.model_dump())
        out = await fill_form(result, target_url=body.target_url, dry_run=body.dry_run)
        out["cid"] = cid
        return out
    except HTTPException:
        raise
    except Exception:
        log.exception("[%s] fill failed", cid)
        raise HTTPException(500, f"form fill failed (cid={cid})")


@app.get("/fill/preview")
async def fill_preview(doc_type: str = "shipping.commercial_invoice"):
    sample = parse_document(
        "Shipper: Acme Exports Pty Ltd\n1 Harbour Rd, Sydney, Australia\n"
        "Consignee: BorderPrint Logistics\n99 Dock St, Melbourne, Australia\n"
        "Invoice Number: INV-1001\nInvoice Date: 15/09/2026\n"
        "Incoterms: FOB Sydney\nCurrency: AUD\n"
        "Subtotal: 1200.00\nFreight: 150.00\nInsurance: 30.00\nTotal: 1380.00\n",
        doc_type if doc_type in DocumentType.__args__ else "shipping.commercial_invoice",  # type: ignore[attr-defined]
    )
    sample.line_items = [LineItem(
        description="Widget A", quantity=10, unit="PCS", unit_price=100.0, amount=1000.0,
    )]
    return {"fields": result_to_fields(sample)}
