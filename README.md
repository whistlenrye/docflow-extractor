# DocFlow Extractor

**Open-source, zero-subscription document extraction engine.** Upload a messy PDF, image, or pasted text, extract structured fields with a free-tier Gemini model, and map them into a target form. Built generic so shipping, invoices, claims, and more are just document types.

> **Owner:** Whistle and Rise (`whistlenrye` on GitHub)
> **Status:** Final / production-ready (not a V1/V2 prototype)
> **Cost:** $0/month on the free tiers. No paid API keys, no subscriptions.

---

## 1. What we're building (evidence & intent)

### The problem
In freight forwarding, a single import shipment can involve a commercial invoice, packing list, bill of lading, and certificate of origin — all arriving in different formats, often from overseas agents. Staff rekey the same fields into the Integrated Cargo System, and one mismatch between documents is the number one cause of clearance delays and storage fees. Shipping Australia has called this manual re-entry a direct drag on the country's trade competitiveness.

The same pattern shows up everywhere: insurance claims, medical intake, loan applications, HR onboarding. Someone reads a document and types the fields into another system. That is the work this project automates.

### The goal
A single, self-contained pipeline that:

1. Accepts an uploaded PDF, image, or pasted text.
2. Detects the document type (or you pick it).
3. Extracts fields into a typed Pydantic schema using a **free-tier Gemini model** (structured output, no regex guessing).
4. Maps those fields into a target form — either via an API POST or browser automation.
5. Shows a before-and-after review so a human confirms before anything is submitted.

### Evidence this is the right problem
- Australian forwarders rekey the exact document types in `samples/` by hand every day.
- Free fillable PDFs of those same types are published by BorderPrint (no signup) — see `samples/README.md`.
- The IDP Leaderboard (Sep 2026) ranks Gemini Flash models at the top for key-information extraction across 16 datasets / 9,229 documents.

---

## 2. Decision log (why each choice)

| Decision | Choice | Why |
|---|---|---|
| Extraction brain | **Gemini 2.5 Flash** (free tier) | Best free-tier accuracy on the IDP Leaderboard; 1M-token context; native structured output via JSON schema; reads PDFs/images directly so no separate OCR step. |
| Structured output | Gemini `response_mime_type=application/json` + Pydantic schema | Guarantees parseable, typed results; one call replaces three regex passes. |
| OCR fallback | Gemini vision (same model) | PaddleOCR was in the V1 stack but adds ~2 GB of deps and is weaker on forms/handwriting than Gemini Flash. Dropped. |
| Backend | FastAPI + Pydantic v2 | Async, typed, tiny surface. |
| Frontend | Next.js App Router + TypeScript | Matches the existing `customs-doc-extractor` sibling; one deploy story. |
| Hosting | Vercel Hobby (frontend) + Render free (backend) | Both free, no card, no subscription. |
| Secrets | `.env` + `.env.example`, never committed | Standard; `.gitignore` blocks `.env`. |
| File limits | 25 MB max, PDF/PNG/JPEG/WEBP only, magic-byte sniff | Prevents zip-bomb / polyglot uploads. |
| CORS | Explicit allowlist via `CORS_ORIGINS` env | `*` was a V1 hole; now locked down. |
| Rate limit | 30 req/min/IP via `slowapi` | Caps free-tier burn and abuse. |
| No DB | Results returned to browser | Keeps the free tier truly zero-cost; no persistence of user docs. |

---

## 3. Security posture

### Scans run
- **GitHub Code Scanning** (CodeQL) — configured via `.github/workflows/codeql.yml`. On this fresh repo it reports **0 open alerts**.
- **Bandit** (Python SAST) — `bandit -r backend/ -ll`. See `SECURITY.md` for the residual findings and why each is accepted or mitigated.
- **npm audit** (frontend) — `npm audit --audit-level=high`. See `SECURITY.md`.
- **Manual review** of upload path, CORS, secrets handling, dependency pins.

### Residual gaps (documented, not hidden)
See **`SECURITY.md`**. Headline items:

1. Free-tier Gemini may train on prompts — do **not** upload documents containing real PII or commercially sensitive data to the free endpoint. Use a paid project or redact first.
2. Render free tier sleeps after 15 min idle and has 512 MB RAM — fine for demos, not high throughput.
3. No auth on the `/extract` endpoint — anyone who finds the URL can burn your free quota. Add an API key or put it behind auth before any public deploy.
4. `raw_text` is truncated to 2,000 chars in the response to limit data exfiltration surface; full text is never persisted.

---

## 4. Run locally

### Prerequisites
- Python 3.11+
- Node 20+
- A free Gemini API key from [Google AI Studio](https://aistudio.google.com/)

### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # paste your GEMINI_API_KEY
uvicorn main:app --reload --port 8000
```
Health check: http://localhost:8000/health

### Frontend
```bash
cd frontend
npm install
cp .env.example .env.local    # BACKEND_URL=http://localhost:8000
npm run dev
```
Open http://localhost:3000

### Test with the sample
1. Open the UI, pick `shipping.commercial_invoice`.
2. Upload nothing — or paste the text from `samples/commercial_invoice_sample.txt`.
3. Hit Extract. You should get a typed `ExtractionResult` with shipper, consignee, line items, totals.

---

## 5. Deploy (free)

```bash
# backend -> Render: connect repo, it reads render.yaml
# frontend -> Vercel: import repo, set BACKEND_URL to the Render URL
```

Set `CORS_ORIGINS` on the backend to your Vercel domain. Set `GEMINI_API_KEY` in Render's env (mark as secret).

---

## 6. Project layout
```
docflow-extractor/
├── README.md                 ← you are here
├── SECURITY.md               ← scan results + residual gaps
├── DECISIONS.md              ← full decision log
├── EVIDENCE.md               ← problem evidence & sources
├── .env.example
├── .gitignore
├── render.yaml
├── .github/workflows/codeql.yml
├── backend/
│   ├── main.py               ← FastAPI app + /extract
│   ├── gemini_client.py      ← Gemini structured-output call
│   ├── extractors.py         ← registry + fallback
│   ├── schemas.py            ← Pydantic models
│   ├── security.py           ← size/type limits, sanitizer
│   └── requirements.txt
├── frontend/
│   ├── app/page.tsx
│   ├── app/api/extract/route.ts
│   └── package.json
└── samples/
    ├── README.md
    └── commercial_invoice_sample.txt
```

## 7. License
MIT.
