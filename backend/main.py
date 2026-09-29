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
