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

## D11. Playwright for form filling (not an API client)
- **Alternatives considered:** direct HTTP POST to the target system's API (fastest, but most customs/ICS endpoints are not public and require per-agency credentials), Selenium (heavier, slower, no first-class async), browser-use / Stagehand (LLM-driven, overkill and costs tokens per field).
- **Why Playwright:** the README's step 4 explicitly called for browser automation; `locator.fill()` is deterministic and cheap; async API fits FastAPI; one pinned version + `playwright install chromium` is reproducible.
- **Headless Chromium only** — no Firefox/WebKit. Cuts the browser download from ~700 MB to ~170 MB, which matters on Render's free tier (512 MB RAM, limited ephemeral disk).
- **Short-lived browser per request** — launch, fill, close. Avoids leaking renderer processes across requests on a memory-constrained box.
- **dry_run mode** — `/fill?dry_run=true` (or `dry_run: true` in the body) returns the field map without launching Chromium, so the mapping can be tested and CI'd without installing browsers.
- **Bundled sample form** (`backend/sample_form.html`) — gives a zero-config target so the pipeline is demonstrable end-to-end before pointing at a real ICS/agency portal.
- **Field-name contract** — the filler matches inputs by `name` attribute. Real target forms will need a thin adapter (or a `FORM_FIELD_MAP` env) because agency portals rarely use our names; the sample form is the reference implementation of that contract.
- **Build-time browser install** — `render.yaml` runs `playwright install chromium && playwright install-deps chromium` during build, with `PLAYWRIGHT_BROWSERS_PATH` pinned so the binary survives deploys. `install-deps` pulls the shared libs Chromium needs on Debian.
- **Accepted risk:** 512 MB is tight. Chromium + FastAPI + Gemini client can approach the ceiling on a busy box; the free tier is for demos, and a real deployment should move to a paid plan or a container with more headroom (documented in SECURITY.md G3/G6).
