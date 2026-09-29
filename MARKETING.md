# Marketing Plan — DocFlow Extractor

Open-source, zero-cost document extraction. The pitch: stop rekeying invoices, packing lists, and bills of lading by hand.

---

## 1. Positioning

**One-liner:** Upload a messy PDF. Get structured fields. Map them into your system. Free, open-source, no subscription.

**Category:** Intelligent Document Processing (IDP) — but the honest wedge is freight forwarding and trade docs, where manual re-entry is a known drag on clearance times.

**Differentiators vs paid IDP (Nanonets, Rossum, Mindee):**
- $0/month. No per-document fees, no seat licenses.
- Self-hosted or free-tier hosted. Your data stays yours (except the free-Gemini caveat in SECURITY.md).
- MIT license. Fork it, extend the schema registry, ship your own document types.
- Built for the exact docs forwarders already handle: commercial invoice, packing list, bill of lading.

**Honest limits (say these out loud — credibility beats hype):**
- Free Gemini tier may train on prompts; don't send real PII or live commercial docs through it.
- No auth on the public `/extract` endpoint yet — add an API key before any real deploy.
- Render free tier sleeps; fine for demos, not production throughput.

---

## 2. Target audiences (priority order)

1. **Australian freight forwarders & customs brokers** — the core pain (ICS rekeying, storage fees from mismatches). Primary ICP.
2. **Indie hackers / solo devs** building internal tools — want extraction without paying for IDP SaaS.
3. **Open-source community** — contributors, stars, forks; the engine that grows the rest.
4. **Adjacent verticals** (insurance claims, medical intake, lending, HR onboarding) — same pipeline, different schemas. Secondary, once shipping docs are proven.

---

## 3. Channels & tactics

### A. GitHub (foundation)
- Keep README sharp: problem → evidence → one-command run → sample. Already strong; maintain it.
- Add a **live demo link** (Vercel + Render) to the top of the README once deployed.
- Topics: `document-extraction`, `idp`, `ocr`, `gemini`, `fastapi`, `nextjs`, `freight`, `customs`, `open-source`.
- Pin a release; write a short changelog so stars convert to trust.

### B. Communities (where the ICP actually hangs out)
- **Freight & logistics:** Freightos Community, Forwarders forums, Australian peak bodies (Customs Brokers & Forwarders Council of Australia — CBCA). Share the problem framing, not a hard sell.
- **Dev:** r/opensource, r/selfhosted, Hacker News "Show HN", Lobsters. Lead with the architecture (Gemini structured output, zero-cost stack) — devs share what they find clever.
- **AI/LLM:** r/LocalLLaMA, AI Twitter/X. Angle: "free-tier Gemini beats paid IDP on the Nanonets leaderboard for KIE."

### C. Content (build the moat)
- One long-form post: *"Why Australian forwarders rekey trade docs by hand — and how to stop."* Publish on your own site or a dev blog; link from README.
- Short demo video (60–90s): upload sample invoice → structured JSON → mapped form. Post to X, LinkedIn, relevant subreddits.
- A comparison table: DocFlow vs Nanonets vs Rossum vs Mindee on price, self-host, schema flexibility, free tier. Keep it factual.

### D. Partnerships & distribution
- **BorderPrint** (sample source): mention them; they may reciprocate or feature it.
- Freight software vendors (CargoWise, Descartes, etc.) — offer a connector/plugin once stable.
- University / TAFE logistics courses — free tool for students learning trade docs.

### E. Paid (only after organic traction)
- Small Google/LinkedIn ads targeting "customs broker software", "freight document management" — AU + NZ first.
- Budget: start at $100–200/mo test; kill anything without a demo signup or star within 14 days.

---

## 4. Funnel & conversion

```
Awareness (HN / X / Reddit / communities)
   → Interest (README + demo video + comparison)
   → Trial (live demo or `git clone` + sample)
   → Adoption (self-host or free deploy)
   → Advocacy (star, fork, contribute a schema)
```

**Primary conversion event:** a star or a successful extract on the live demo. Track both.

**Secondary:** GitHub issues filed, PRs merged, emails from forwarders asking about production use.

---

## 5. 30 / 60 / 90 day plan

**Days 1–30 — Ship the story**
- Deploy live demo (Vercel + Render), link it in README.
- Post Show HN + one X thread + one Reddit post (r/opensource or r/selfhosted).
- Write the long-form problem post.
- Goal: 50+ stars, 5+ demo runs, 1–2 inbound messages.

**Days 31–60 — Prove the wedge**
- Add 1–2 more document types (packing list, bill of lading) with samples.
- Engage CBCA / freight forums with a helpful (non-salesy) post.
- Collect 2–3 testimonials or before/after screenshots (with permission).
- Goal: 150+ stars, first production enquiry.

**Days 61–90 — Compound**
- Publish comparison table + architecture deep-dive.
- Approach 1 freight-software vendor about a connector.
- Start a tiny paid test only if organic is converting.
- Goal: 300+ stars, 1 partnership conversation, repeatable content cadence.

---

## 6. Metrics to watch

| Metric | Why | Target (90d) |
|---|---|---|
| GitHub stars | Awareness + credibility | 300 |
| Live demo runs / week | Product-market signal | 20 |
| Inbound emails / issues | Real demand | 5 |
| Forks | Extensibility interest | 10 |
| Time-to-first-extract (demo) | Friction | < 60s |

---

## 7. What not to do

- Don't claim "AI-powered" without the evidence link (IDP Leaderboard). Devs smell hype.
- Don't hide the free-tier data-use caveat — forwarders will ask, and honesty converts.
- Don't spray every channel at once. Start with GitHub + one community + one post.
- Don't pay for ads before the demo and README are airtight.

---

*Last updated: 2026-09-29. Revisit after the 30-day mark.*
