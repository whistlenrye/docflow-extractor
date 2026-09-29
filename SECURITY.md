# Security

## Scans

| Tool | Scope | Result |
|---|---|---|
| GitHub CodeQL | `.github/workflows/codeql.yml` on push/PR | **0 open alerts** (fresh analysis) |
| Bandit (`-ll`) | `backend/` | 2 low findings, both accepted — see below |
| `npm audit --audit-level=high` | `frontend/` | **0 high/critical** |
| Manual review | upload path, CORS, secrets, deps | documented |

## Bandit findings (accepted)

1. **B110** — pdfplumber failures are caught, logged, and the request continues on the parser / Gemini path. Non-fatal by design. Magic-byte checks raise `HTTPException` (no `assert`).

## Residual gaps (intentional, documented)

### G1 — Free-tier Gemini data use
Google's free tier may use prompts to improve products. **Do not** send real PII or commercially sensitive documents through the free endpoint. For production data, move the project to a paid AI Studio tier (data not used for training) or self-host a model.

### G2 — Optional API key
If `EXTRACT_API_KEY` is unset, `/extract` and `/fill` are open and can burn a free Gemini quota. **Set `EXTRACT_API_KEY` before any public deploy.** When it is set, requests must send a matching `X-API-Key` header (`secrets.compare_digest`). The Next proxy attaches the key from its own env so the browser never sees it.

### G3 — Render free tier limits
512 MB RAM, sleeps after 15 min idle, no SLA. Suitable for demos and low traffic. For sustained load, upgrade the Render plan or move the backend to a small VPS.

### G4 — `raw_text` truncation
The API returns at most 2,000 chars of source text to limit the data-exfiltration surface if the response is logged or cached by a third party. Full text is never written to disk or a database.

### G5 — Dependency freshness
Pins are from Sep 2026. Re-run `pip list --outdated` and `npm outdated` monthly; the CodeQL workflow will flag newly disclosed vulns in dependencies.

### G6 — Playwright on the free tier (new)
Chromium adds ~170 MB to the image and ~150–250 MB RSS at runtime. Combined with FastAPI + the Gemini client this sits close to the 512 MB ceiling, so concurrent fills or a cold start under memory pressure can OOM. **Mitigations in place:** headless Chromium only, one browser per request then closed, `PLAYWRIGHT_BROWSERS_PATH` pinned to ephemeral disk. **Before any real traffic:** move to a paid Render plan (2 GB+) or run the filler in a separate worker with more headroom. The `/fill` endpoint is rate-limited like `/extract`.

### G7 — Target-form SSRF surface
`/fill` navigates the server browser to `target_url`. `url_safety.assert_safe_target` rejects non-http(s) URLs, cloud-metadata hosts, and any resolved private, link-local, reserved, or multicast address. Loopback is allowed only when `ALLOW_LOCAL_FORM_TARGETS=1` (the default, so the bundled sample form works). The final page URL is checked again after navigation. A redirect racing a DNS change is still a residual risk; keep the endpoint behind the API key (G2) on any public host.

## What we hardened vs V1
- CORS: `*` → explicit `CORS_ORIGINS` allowlist.
- Upload: no size/type check → 25 MB cap + magic-byte sniff + extension allowlist.
- Secrets: hardcoded none → `.env` + `.env.example`, gitignored.
- Rate limit: none → 30 req/min/IP.
- Error leakage: stack traces could surface → generic 500 with correlation id.
- Form filling: none → Playwright headless Chromium, short-lived per request, dry-run mode for CI.
