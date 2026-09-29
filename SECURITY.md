# Security

## Scans

| Tool | Scope | Result |
|---|---|---|
| GitHub CodeQL | `.github/workflows/codeql.yml` on push/PR | **0 open alerts** (fresh analysis) |
| Bandit (`-ll`) | `backend/` | 2 low findings, both accepted — see below |
| `npm audit --audit-level=high` | `frontend/` | **0 high/critical** |
| Manual review | upload path, CORS, secrets, deps | documented |

## Bandit findings (accepted)

1. **B101** — `assert` used in `security.py` for magic-byte checks.
   *Accepted:* asserts are stripped with `python -O`; the check is also enforced via an explicit `if` that raises `HTTPException`. Defense in depth.
2. **B110** — try/except that returns `None` around pdfplumber open.
   *Accepted:* intentional fallback to the Gemini vision path; failure is non-fatal and logged.

## Residual gaps (intentional, documented)

### G1 — Free-tier Gemini data use
Google's free tier may use prompts to improve products. **Do not** send real PII or commercially sensitive documents through the free endpoint. For production data, move the project to a paid AI Studio tier (data not used for training) or self-host a model.

### G2 — No authentication on `/extract`
The endpoint is open. Anyone who discovers the deployed URL can burn the 1,500 req/day free quota. **Mitigation before public deploy:** add an `X-API-Key` header check (env `EXTRACT_API_KEY`) or put the service behind a reverse proxy with basic auth. Skeleton is commented in `main.py`.

### G3 — Render free tier limits
512 MB RAM, sleeps after 15 min idle, no SLA. Suitable for demos and low traffic. For sustained load, upgrade the Render plan or move the backend to a small VPS.

### G4 — `raw_text` truncation
The API returns at most 2,000 chars of source text to limit the data-exfiltration surface if the response is logged or cached by a third party. Full text is never written to disk or a database.

### G5 — Dependency freshness
Pins are from Sep 2026. Re-run `pip list --outdated` and `npm outdated` monthly; the CodeQL workflow will flag newly disclosed vulns in dependencies.

## What we hardened vs V1
- CORS: `*` → explicit `CORS_ORIGINS` allowlist.
- Upload: no size/type check → 25 MB cap + magic-byte sniff + extension allowlist.
- Secrets: hardcoded none → `.env` + `.env.example`, gitignored.
- Rate limit: none → 30 req/min/IP.
- Error leakage: stack traces could surface → generic 500 with correlation id.
