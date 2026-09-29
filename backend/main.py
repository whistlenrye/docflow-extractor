from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import pdfplumber
import fitz  # PyMuPDF
from schemas import DocumentType, ExtractionResult
from extractors import get_extractor

app = FastAPI(title="DocFlow Extractor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/extract", response_model=ExtractionResult)
async def extract(
    file: UploadFile = File(...),
    doc_type: Optional[str] = Form(None),
):
    raw = await file.read()
    text = ""
    # Try text extraction first (digital PDFs)
    try:
        with pdfplumber.open(file=raw) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
                for table in page.extract_tables() or []:
                    for row in table:
                        text += " " + " ".join(str(c) for c in row if c)
    except Exception:
        pass
    # Fallback: render pages and OCR (scanned PDFs)
    if len(text.strip()) < 50:
        doc = fitz.open(stream=raw, filetype="pdf")
        for page in doc:
            pix = page.get_pixmap(dpi=200)
            # OCR would run here via PaddleOCR; placeholder keeps it dependency-light
            text += page.get_text()
    detected = doc_type or "generic.invoice"
    extractor = get_extractor(detected)
    return extractor.extract(text, detected)
