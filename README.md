# DocFlow Extractor

Open-source, zero-cost document extraction engine. Upload a messy PDF or email, extract structured fields, and map them into a target form. Built generic so shipping, invoices, claims, and more are just document types.

## The problem

In freight forwarding, a single import shipment can involve a commercial invoice, packing list, bill of lading, and certificate of origin — all arriving in different formats, often from overseas agents. Staff rekey the same fields into the Integrated Cargo System, and one mismatch between documents is the number one cause of clearance delays and storage fees. Shipping Australia has called this manual re-entry a direct drag on the country's trade competitiveness.

The same pattern shows up everywhere: insurance claims, medical intake, loan applications, HR onboarding. Someone reads a document and types the fields into another system. That is the work this project automates.

## What it does

1. Accepts an uploaded PDF, image, or pasted text.
2. Detects the document type (or you pick it).
3. Extracts fields into a typed schema using open-source libraries only.
4. Maps those fields into a target form — either via an API POST or browser automation.
5. Shows a before-and-after review so a human confirms before anything is submitted.

## Document types (extensible)

Shipping is the first vertical. Each type is a schema plus an extractor, registered in one place:

| Type | Key fields extracted |
|---|---|
| `shipping.commercial_invoice` | shipper, consignee, invoice number, date, line items, HS codes, origin, Incoterms, totals |
| `shipping.packing_list` | packages, net/gross weight, dimensions, marks |
| `shipping.bill_of_lading` | carrier, vessel, ports, container, seal, B/L number |
| `generic.invoice` | vendor, buyer, line items, tax, totals, payment terms |
| `generic.claim` | claimant, policy, incident date, amounts, description |

Adding a new type means adding one schema file and one extractor. No core changes.

## Stack (all free, no subscription)

**Frontend (Next.js)**
- Next.js App Router + TypeScript
- Tailwind CSS
- Upload UI, field review, mapping preview

**Backend (Python, called from Next.js API routes)**
- FastAPI for the extraction service
- pdfplumber / PyMuPDF for text and table extraction
- PaddleOCR (Apache 2.0) for scanned PDFs — runs locally, no API key
- Pydantic for typed schemas
- Playwright for browser-based form filling when no API exists

**Hosting (all free tiers, no credit card)**
- Frontend: Vercel Hobby (100 GB transfer, personal use)
- Backend: Render free web service (512 MB RAM, sleeps after 15 min idle) or Koyeb
- No database required for v1 — extracted results are returned to the browser

## Constraints honored

- No paid API keys. OCR and extraction run on your own hardware or the free host.
- No subscriptions. Every library is MIT, Apache 2.0, or AGPL.
- No upfront cost. Deploy from the repo, get a URL.

## Sample data

See `samples/`. A synthetic commercial invoice PDF is included so you can test extraction end to end without real documents. Real-world samples can be downloaded free (no signup) from BorderPrint's fillable forms.

## Run locally

```bash
# backend
cd backend && pip install -r requirements.txt
uvicorn main:app --reload

# frontend
cd frontend && npm install && npm run dev
```

## License

MIT.
