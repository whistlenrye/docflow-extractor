from __future__ import annotations
import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from schemas import ExtractionResult, DocumentType
from extractors import get_extractor
from gemini_client import extract_with_gemini
from security import read_limited, sniff_type, sanitize_filename, new_correlation_id
from form_filler import fill_form, result_to_fields

load_dotenv()

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("docflow")

limiter = Limiter(key_func=get_remote_address, default_limits=[
    f"{os.getenv('RATE_LIMIT_PER_MIN', '30')}/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("DocFlow backend starting; model=%s", os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
    yield


app = FastAPI(title="DocFlow Extractor", version="1.0.0", lifespan=lifespan)
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

MIME = {"pdf": "application/pdf", "png": "image/png",
        "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}


@app.get("/health")
def health():
    return {"status": "ok", "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash")}


@app.post("/extract", response_model=ExtractionResult)
@limiter.limit(f"{os.getenv('RATE_LIMIT_PER_MIN', '30')}/minute")
async def extract(request: Request,
                  file: UploadFile = File(...),
                  doc_type: str | None = Form(None)):
    cid = new_correlation_id()
    try:
        # optional API key gate (uncomment to enforce):
        # if os.getenv("EXTRACT_API_KEY") and request.headers.get("X-API-Key") != os.getenv("EXTRACT_API_KEY"):
        #     raise HTTPException(401, "invalid api key")

        raw = await read_limited(file)
        fname = sanitize_filename(file.filename)
        ext = sniff_type(raw, fname)
        mime = MIME[ext]

        text = ""
        try:
            import pdfplumber
            with pdfplumber.open(file=raw) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
        except Exception:
            pass

        detected = doc_type or "generic.invoice"
        if detected not in DocumentType.__args__:  # type: ignore
            raise HTTPException(400, f"Unknown doc_type: {detected}")

        try:
            result = extract_with_gemini(text, detected, raw, mime)
        except Exception as e:
            log.warning("[%s] gemini failed, falling back: %s", cid, e)
            result = get_extractor(detected).extract(text, detected)
            result.warnings = list(result.warnings) + [f"Gemini error (cid={cid}): {type(e).__name__}"]

        result.raw_text = (text or "")[:2000]
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.exception("[%s] unhandled", cid)
        return JSONResponse(status_code=500,
                            content={"detail": "extraction failed", "cid": cid})


class FillRequest(ExtractionResult):
    """Reuses the extraction schema so the client can POST the same JSON it got back."""
    target_url: str | None = None
    dry_run: bool = False


@app.post("/fill")
@limiter.limit(f"{os.getenv('RATE_LIMIT_PER_MIN', '30')}/minute")
async def fill(request: Request, body: FillRequest):
    """Map extracted fields into a target web form via Playwright.

    Accepts an ExtractionResult (the same shape /extract returns) plus an
    optional target_url and dry_run flag. dry_run skips launching Chromium.
    """
    cid = new_correlation_id()
    try:
        result = ExtractionResult.model_validate(body.model_dump())
        out = await fill_form(result, target_url=body.target_url, dry_run=body.dry_run)
        out["cid"] = cid
        return out
    except Exception as e:
        log.exception("[%s] fill failed", cid)
        raise HTTPException(500, f"form fill failed (cid={cid}): {type(e).__name__}")


@app.get("/fill/preview")
async def fill_preview(doc_type: str = "shipping.commercial_invoice"):
    """Return the field map a sample extraction would produce, no browser."""
    sample = ExtractionResult(
        doc_type=doc_type, confidence=0.9,
        shipper={"name": "Acme Exports Pty Ltd", "address": "1 Harbour Rd, Sydney", "country": "AU"},
        consignee={"name": "BorderPrint Logistics", "address": "99 Dock St, Melbourne", "country": "AU"},
        invoice_number="INV-1001", invoice_date="2026-09-15", incoterms="FOB Sydney",
        currency="AUD", subtotal=1200.0, freight=150.0, insurance=30.0, total=1380.0,
        line_items=[{"description": "Widget A", "quantity": 10, "unit": "PCS", "unit_price": 100.0, "amount": 1000.0}],
    )
    return {"fields": result_to_fields(sample)}
