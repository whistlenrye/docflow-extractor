# Decision Log

Full rationale for every non-obvious choice. Read this when you want to change something — the "why" is here so you don't re-litigate it.

## D1. Model: Gemini 2.5 Flash (free tier)
- **Alternatives considered:** Groq (text-only, needs a separate parser), OpenRouter free models (weaker on tables/forms), self-hosted Qwen2.5-VL (needs a GPU), PaddleOCR alone (no field understanding).
- **Why Gemini:** tops the IDP Leaderboard (Sep 2026) for key-information extraction; 1M context; reads PDF/image bytes natively; structured output via JSON schema is first-class.
- **Free-tier limits (approx):** 1,500 req/day, 10 RPM, 250k TPM. Enough for demos and low traffic; documented in SECURITY.md G3.

## D2. Structured output over regex
- V1 used regex (`extractors.py`). It broke on every new layout.
- Gemini `response_mime_type=application/json` + `response_json_schema=ExtractionResult.model_json_schema()` guarantees typed, validated output. One call, no post-processing.

## D3. Drop PaddleOCR
- V1 pinned `paddleocr==2.8.1` + `paddlepaddle==2.6.2` (~2 GB, fragile CPU wheels).
- Gemini vision matches or beats it on forms/handwriting (IDP Leaderboard) and removes the dependency entirely. Kept pdfplumber/PyMuPDF only as a cheap text-layer fast path.

## D4. No database
- Results are returned to the browser and discarded. Avoids any persistence of user documents, keeps the free tier truly zero-cost, and removes a whole attack surface (SQL injection, backups, retention policy).

## D5. CORS allowlist
- V1: `allow_origins=["*"]`.
- Final: `CORS_ORIGINS` env, defaulting to localhost. `*` + credentials is a known browser hole; we never combine them.

## D6. Upload hardening
- 25 MB hard cap (Gemini inline limit is 20 MB; we allow a little headroom for the text-layer path).
- Magic-byte sniff (`%PDF`, PNG/JPEG/WEBP signatures) instead of trusting the extension — blocks polyglot uploads.
- Filename sanitized; never used in paths.

## D7. Rate limiting
- `slowapi`, 30 req/min/IP. Caps both abuse and accidental free-tier burn. Tunable via env.

## D8. Secrets
- `.env` gitignored, `.env.example` committed with placeholders. `GEMINI_API_KEY` read at runtime; never logged. Render/Vercel store it as a secret env var.

## D9. Error handling
- All exceptions caught at the route boundary → generic 500 + correlation id. No stack traces to clients. Logged server-side with the id for debugging.

## D10. Repo ownership
- Lives under the `whistlenrye` GitHub account (Whistle and Rise), not a personal account. Keeps company IP and access control in one place.
