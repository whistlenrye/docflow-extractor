# Evidence

Sources and data backing the problem statement and the model choice.

## Problem evidence
- **Shipping Australia** has publicly flagged manual re-entry of trade documents as a drag on national trade competitiveness (industry submissions to the ACCC/DAWE consultations, 2023–2025).
- **BorderPrint** publishes free, no-signup fillable PDFs for exactly the document types we target:
  - Commercial Invoice, Packing List, Bill of Lading (see `samples/README.md` for links).
- The pattern (read document → type fields into another system) is identical in insurance claims, medical intake, lending, and HR onboarding — same automation applies.

## Model evidence
- **IDP Leaderboard** (Nanonets, refreshed Sep 2026): Gemini 2.5 Flash ranks #1 overall across OCR, KIE, classification, VQA, table extraction, and confidence scoring on 16 datasets / 9,229 documents.
- **Dr.DocBench** (Aug 2026): Gemini 3.1 Pro leads the general-VLM group on text/formula/table extraction; Flash variants are the cost-effective proxy.
- **Gemini structured outputs** (Google, Nov 2025 announcement): full JSON Schema support including `anyOf`, `$ref`, numeric bounds — sufficient for our Pydantic schemas.
- **Free-tier terms:** Google AI Studio free tier, no credit card, no expiry; data-use statement notes free-tier prompts may improve products (hence SECURITY.md G1).

## Sample data
- `samples/commercial_invoice_sample.txt` is synthetic — no real personal or commercial data. Safe to commit and to run against the free endpoint.
