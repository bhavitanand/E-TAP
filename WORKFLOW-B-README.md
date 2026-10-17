# Workflow B — E-TAP correctness, evidence, privacy and reliability

**Purpose:** This is the single consolidated record for Workflow B. It replaces the separate `B0-CHANGES.md`, `B1-B9-CHANGES.md`, `B2-CHANGES.md`, and `B5-B6-B10-CHANGES.md` notes. Keep future Workflow B implementation notes, validation results and limitations in this file rather than creating a new file for each B stage.

**Scope boundary:** Workflow B improves the existing email-analysis experience and its correctness, evidence quality, privacy, and service reliability. The dynamic execution sandbox / detonation environment is Workstream A and is intentionally not implemented here. A sandbox should contribute runtime evidence into E-TAP's report rather than duplicate the static pipeline.

**Current deployment (team demo):**
- Frontend: <https://e-tap-lac.vercel.app/>
- Backend liveness: <https://etap-backend-od1c.onrender.com/health>
- Backend readiness: <https://etap-backend-od1c.onrender.com/ready>
- API documentation: <https://etap-backend-od1c.onrender.com/docs>

These URLs are the team's current configuration, not immutable service guarantees.

---

## 1. Workflow B status at a glance

| Work package | Current implementation | Important limitation |
|---|---|---|
| B0 — truthfulness and safe failure behavior | Canonical verdict bands, quick-content-check mode, click-to-analyze extension, scrubbed errors, no automatic “clean” result from failed lookups | Extension still analyzes reconstructed visible content, not the original Gmail RFC 822 message |
| B1 — evidence model | Deterministic evidence ledger and `evidence_report`; observed facts, reputation results, model inference and unavailable evidence are separated | Evidence quality depends on what the source artifact actually contains |
| B2 — evaluation and offline fallback | Labelled-corpus evaluation utilities; offline fallback no longer calls every URL malicious; malformed MIME charset recovery | The checked-in 24-message result is a historical pre-fix baseline, not current detection performance |
| Existing forensic pipeline | Headers/authentication when available, received-chain, IOC extraction, attachment signatures/hashes, macro/static checks, OCR/QR, reputation enrichment and campaign correlation | Coverage varies with input format, installed libraries, live provider availability and analysis mode |
| B5 — link text vs destination | HTML link-text/`href` comparison and explainable destination heuristics | Redirects are not followed; inferred destinations are labelled as inferred, not observed |
| B6 — QR trace | Per-image QR status and decoded destinations; QR presence alone is not treated as proof of maliciousness | Decoder availability and image quality affect coverage; decoded URLs still need contextual evaluation |
| B9 — “observed / why it matters / what to do” | Evidence-first narrative, conservative fixed actions, separately labelled AI suggestions | Guidance is triage assistance; it cannot determine compromise merely from a click or a missing signal |
| B10 — privacy and external enrichment | Privacy report describes processing, storage and external lookup flows; sensitive URL lookups can be trimmed or skipped; external Gemini context receives URL sanitization | Sanitization is heuristic defense-in-depth, not a guarantee; email-derived text can still be sent to Gemini, and stored IOC data needs retention controls |
| B11 — provider status and service readiness | Per-provider statuses, timeouts/rate limits/configuration gaps, analysis duration, `/health` liveness and `/ready` database readiness | Mocked status tests do not replace a live hosted smoke test; free hosting can still cold-start or run out of resources |

The B11 provider status is **separate from the threat verdict**. If the analysis completed but providers failed, the report must say so; a failed, skipped, disabled or unknown check must never be presented as a clean result.

---

## 2. B0 — Verdict consistency and safe failure behavior

### Implemented

- Verdicts are normalized to the canonical labels and score bands in `backend/verdicts.py`; the more severe of the label and score wins so a benign-looking label cannot hide a high risk score.
- Danger styling uses the same threshold across the dashboard, history cards, PDF export and extension UI.
- The extension adds an **Analyze this email** button. Message content is read and submitted only after the user clicks it; there is no periodic content-scanning loop.
- The extension sends `source=quick_content_check` so the backend does not pretend its reconstructed message contains the original authentication headers or routing history.
- Quick-content-check mode marks unavailable header evidence as unavailable, does not run SPF/DKIM/DMARC as if original headers existed, and does not use the metadata-only “safe” triage bypass.
- Provider failures return an unknown result rather than `malicious: false`; transient failures are not cached as if they were reputation answers.
- The UI distinguishes the assessment provider and fallback path. Raw model exception text is not intended for the user-facing result.
- Backend diagnostic logging avoids printing email bodies, extracted URLs and matched risky keywords.

### Behavior to preserve

- A quick content check is not full-message forensics.
- A lookup failure is missing evidence, not a benign finding.
- “No high-risk indicators found in the available evidence” is not the same claim as “safe.”
- The extension’s `View Full Report` link must open the hosted dashboard in the committed extension configuration; for local development, both extension URL constants must be changed and the unpacked extension reloaded.

## 3. B1 / B9 — Evidence Ledger and actionable explanations

### Evidence model

`backend/evidence.py` constructs structured evidence from parsed fields and downstream results. Each finding identifies its kind/source, status, risk direction, strength, title, detail and reason. Deterministic observations are not delegated to the model.

- `observed`, `reputation` and `ai_inferred` findings remain distinguishable.
- `present`, `absent` and `unavailable` are different states. Unavailable information does not lower risk.
- Reputation results are qualified: unknown or unscanned does not mean clean; a small number of engine detections should not be overstated; successful authentication alone does not prove content is safe.
- AI findings must cite evidence identifiers. Invalid identifiers are dropped; unsupported AI claims cannot become headline evidence.
- The report’s `evidence_state` is one of `high_risk_evidence`, `suspicious_uncertain` or `no_high_risk_found`; it intentionally avoids a categorical “safe” state.
- Confidence is capped when the report has material limitations, such as quick-check input, unavailable threat intelligence or deterministic fallback.

### User report

The report presents:

1. **What we observed** — evidence and checks not available.
2. **Why it matters** — the highest-value findings and evidence pointing the other way.
3. **What you should do** — conservative, actionable guidance.

AI-written interpretation and AI-suggested actions are separately labelled from deterministic evidence and fixed guidance. The extension uses a condensed version of the same evidence report and has a fallback presentation for older backend reports.

### API and persistence

`POST /analyze` returns `evidence_report`; the analysis record persists it. `GET /investigations/{email_id}` returns the stored report when available and can rebuild a limited report for an older record from fields that were actually stored. Such reports are marked as reconstructed; evidence that was never stored (for example original HTML or images) cannot be recreated later.

## 4. B2 — Evaluation, fallback behavior and parser recovery

### Evaluation tools

- `backend/eval/corpus.py` loads labelled `.json` parsed-email fixtures or authorized local `.eml` files, drops exact duplicates and reports unlabelled inputs.
- `backend/eval/metrics.py` calculates confusion counts, false-positive/false-negative rates, Wilson 95% intervals and threshold sweeps.
- `backend/eval/run_eval.py` runs the pipeline in a controlled offline/fake-database configuration and writes a JSON result and Markdown report.

Run a new evaluation after changes to parser behavior, verdict thresholds or offline classification:

```powershell
cd backend
$env:USE_FAKE_DB = "1"
$env:AUTO_FALLBACK_DB = "0"
$env:THREAT_INTEL_LIVE = "0"
Remove-Item Env:GEMINI_API_KEY -ErrorAction SilentlyContinue
python -m eval.run_eval
```

Use the exact command supported by the installed project version; if the runner requires corpus paths, supply an authorized corpus explicitly. Raw corpus files are not guaranteed to be included in a fresh clone.

### Offline classifier correction

The deterministic offline fallback no longer treats the presence of any URL as a malicious-link verdict. It looks for converging signals such as a link call-to-action plus a sensitive or urgent request. An empty/unreadable message is marked as input-incomplete and is not labelled legitimate solely because no body was parsed.

This heuristic is still only a fallback. It is not a trained classifier and should not be described as equivalent to Gemini or a full forensic review.

### Charset recovery

`backend/email_parser/eml_parser.py` retries MIME text decoding when an artifact declares an unsupported charset (for example `charset=DEFAULT`). It preserves readable text where possible and records a parse warning instead of silently producing an empty body. Warnings are diagnostic context; they are not by themselves proof of phishing.

### Evaluation results (offline-only, 24-message fixture)

`backend/eval/results/report.md` and `results.json` are from a **post-fix, offline-only** run (no Gemini, no live threat intel, XGBoost triage available). This is a debugging fixture (15 benign, 9 spam; mostly 2002-era bulk spam, not link-based phishing), not a benchmark.

| Run | Benign flagged as danger (FP) | Spam flagged as danger (FN) |
|---|---|---|
| Pre-fix baseline | 13 / 15 | 2 / 9 |
| Post-fix (current) | 1 / 15 | 9 / 9 |

The fixes removed the "any URL = malicious" over-flagging, but the offline fallback is now **conservative to the point of missing all of this fixture's spam**; most of it lands in `LOW RISK` / `no_high_risk_found`. That is partly expected (the fallback targets link-plus-credential phishing, not generic bulk spam, and two spam messages still reach the pipeline with empty bodies), but it means the offline fallback must not be described as a spam or phishing detector. Thresholds were deliberately not tuned on 24 messages. Before any accuracy claim, rerun `python -m eval.run_eval <corpus> --use-gemini --live-threat-intel` on an authorized, broader labelled corpus that includes real phishing.

## 5. Static forensics already in E-TAP (not the dynamic sandbox)

The dynamic sandbox assigned to Workstream A is not part of these changes. Workflow B builds on these static/existing components:

- `.eml`/`.msg` parsing and normalization.
- Header and authentication-result analysis, when original headers are available.
- Received-chain inspection.
- IOC extraction for IPs, domains, URLs and hashes.
- Attachment hash/signature/type checks and static macro-oriented analysis.
- OCR and QR decoding where supported dependencies are available.
- Optional VirusTotal, AbuseIPDB, WHOIS and IP-geolocation enrichment.
- XGBoost metadata triage, Gemini interpretation and deterministic fallback.
- MongoDB persistence and campaign/IOC correlation.

These checks do not execute suspicious attachments. Static findings may justify deeper review, but they do not substitute for runtime observation. A sandbox's future output should be supplied as a distinct evidence source and should not overwrite the original observations.

## 6. B5 — Link text, URL destination and redirect claims

`backend/forensics/link_analysis.py` compares HTML anchor text (and relevant image-alt text) with the actual `href` when an HTML body is available. Checks include destination/text mismatch, URL user-info tricks, look-alike or mixed-script domains, punycode, bare IPs, shorteners, unusual ports, script/data URL schemes and redirect-style parameters.

- Redirects are **not followed** by this analysis. `resolution.status` is `not_resolved`.
- Redirect parameters may expose an `inferred_target_host`; it is explicitly an inference, not a visited or observed destination.
- A link-text mismatch on its own is weak evidence because legitimate tracking links exist.
- Text-only messages and the extension’s Quick Content Check do not supply the same HTML link-target coverage as an original HTML artifact; that limitation is shown as not checked.
- Any future redirect resolver must have SSRF protections, bounded redirects/timeouts and a safe network policy before it is enabled.

## 7. B6 — QR trace

The image-forensics path exposes QR status such as `decoded`, `no_qr_found`, `decoder_unavailable`, `image_unreadable` or `scan_failed`, plus decoded payloads where available. `backend/forensics/qr_trace.py` links the image source to its decoded payload and then evaluates the destination with the existing link checks.

- The presence of a QR code alone is not a malicious verdict.
- A decoded, suspicious destination is stronger evidence than the image type alone.
- An undecodable image is unavailable evidence, not evidence that the image is clean.
- Recipient-specific/personalized URL values are highlighted without displaying sensitive query values unnecessarily.
- OCR/QR coverage depends on the installed decoder libraries and the quality/format of the input image.

## 8. B10 — Privacy and third-party data flows

`backend/privacy.py` creates a `privacy_report` that identifies the processing/storage/enrichment data flows and the URL lookup outcome. The report is returned from `/analyze`, persisted with the record and returned from `/investigations/{email_id}`. The report UI and PDF export include the privacy block.

### VirusTotal URL policy

- A URL can be queried in full, queried after removing the query/fragment, or skipped when it appears to contain sensitive values or an internal/private destination.
- Skipped URLs return `malicious: null` and a skip status; they are not cached as a clean result and are not echoed with secret-bearing query strings.
- The URL report explains when lookups were skipped by privacy policy, missing keys, local quota limits or provider limits. Provider-flow `count` reflects outbound requests; cached responses, failed attempts, missing configuration and intentional skips are reported separately rather than being presented as data sent.
- URL sanitization for Gemini removes query/fragment details and reduces secret-looking destinations to a conservative representation. This is heuristic: other email-derived fields and text can still contain sensitive content.

### What this does not guarantee

- The hosted application is not local-only. A hosted backend processes uploaded content; Gemini may receive email-derived text/evidence; threat-intelligence providers receive queried indicators; MongoDB stores investigation records and extracted data according to the persistence schema.
- No heuristic can guarantee that all tokens or personal information will be recognized.
- A visible privacy report is not a substitute for reviewing provider terms, access controls, retention, deletion and legal requirements.
- Do not use sensitive production inboxes with the public demo until server-side access controls and data-handling policies have been reviewed.

## 9. B11 — Provider status, timeouts and health/readiness checks

### Per-analysis provider status

`backend/provider_status.py` adds a normalized `provider_status` object to analysis reports and stores it with the investigation. It is separate from the threat verdict and includes a safe status/summary for:

- Gemini (including requested model, model used, fallback, timeout, quota/rate-limit or triage skip).
- VirusTotal (URL/hash lookups).
- AbuseIPDB (public-IP reputation).
- WHOIS/domain data.
- IP geolocation.

Provider/lookup outcomes distinguish successful answers, unknown/no-record answers, provider failures, timeouts, rate limits, missing configuration, disabled lookups, privacy skips and policy/limit skips. A VirusTotal “not found” result is an answer of **unknown**, not “clean.” When analysis finishes despite failures, the summary can read `Analysis completed; 2 providers unavailable.` Skipped and disabled checks are not counted as provider outages, but are reported as coverage gaps so the UI does not label missing evidence as complete coverage.

`analysis_duration_ms` is recorded with provider status. Error summaries sent to users do not include raw provider exception details or credential-bearing request strings.

### Health endpoints

- `GET /` — service index.
- `GET /health` — liveness only; proves the HTTP process can answer.
- `GET /ready` — readiness check; pings MongoDB and returns HTTP 503 if the configured database is unavailable. In `USE_FAKE_DB=1` mode it reports the in-memory test database explicitly.

The dashboard engine indicator uses `/ready`, not just `/health`, so a live process with an unavailable database is not shown as fully ready. Vite proxies `/ready` locally. Render's health-check path is `/health`; readiness can be checked separately in a browser or monitoring tool.

### Bounded external work

- `GEMINI_REQUEST_TIMEOUT_MS` defaults to 8000 ms and is clamped to 1000–60000 ms per Gemini request.
- `THREAT_INTEL_MAX_LOOKUPS_PER_PROVIDER` defaults to 2 indicators per provider per analysis and is clamped to 1–20.
- AbuseIPDB, WHOIS, VirusTotal and geolocation requests use bounded calls where supported. VirusTotal also has a process-local request limiter; that limiter is not distributed across multiple backend instances.
- Provider failures and limits must degrade the report, not crash the entire investigation or turn unknown into benign.

### Test coverage added

`backend/tests/test_provider_status.py` covers provider timeouts, rate limits, skipped and disabled checks, unavailable providers, unknown VirusTotal results, Gemini skipped by triage, missing keys, and protection from raw exception leakage. `backend/tests/test_api_chat.py` covers `/`, `/health` and `/ready` in a fully installed test environment.

## 10. Public demo limitations and pre-Workflow-C gate

Do not treat a green health indicator or successful single demo analysis as a security review. The following must be closed or explicitly accepted before the app handles sensitive email or is used by multiple real users:

- [ ] **Authentication/authorization:** the reviewed API routes `/analyze`, `/chat` and `/investigations/{email_id}` do not establish full per-user identity/isolation. CORS and IP rate limits are not authentication. Historical RAG can search shared stored investigations. Add server-side authorization or keep the public deployment restricted to synthetic/non-sensitive test data and disable/restrict historical access until secure.
- [ ] **End-to-end privacy review:** validate what is sent to Gemini, providers, Render logs and MongoDB; define retention/deletion; test secret-bearing URLs and redaction; do not claim zero data leakage based solely on a privacy report.
- [x] **Fresh frontend build:** verified (see validation below).  
  _Original note:_ run `npm ci` and `npm run build` from `frontend/` in the team's network-enabled environment after these code changes. The packaging environment used for this ZIP could not complete `npm ci` because the package-registry request timed out; therefore a fresh Vite build was not independently confirmed here.
- [x] **Full backend suite:** verified, 102/102 passing (see validation below).  
  _Original note:_ run the commands below in a clean environment after `python -m pip install -r backend/requirements.txt`. A partial system environment without `extract_msg` and `slowapi` failed test collection; this was a missing-dependency collection issue, not a successful full-suite run.
- [ ] **Post-deploy smoke test:** after committing/pushing, rebuild Render and Vercel as needed; check `/ready`, analyze one benign synthetic email and one phishing fixture, confirm MongoDB persistence, verify provider failure status using mocked local tests or a safe staging setup, and test the SOC Assistant.
- [ ] **Evaluation refresh (partially done):** the 24-message fixture was rerun on the fixed code (results above). Still needed: an authorized, broader labelled corpus that includes real phishing, ideally with Gemini and live threat intel enabled.
- [ ] **Extension scope:** maintain the click-to-analyze action and the Quick Content Check warning. The extension reconstructs visible content; it does not preserve original headers, complete HTML link targets or attachments. Proper Gmail API retrieval needs a separate OAuth/security review.

### Suggested regression commands

Run from `backend/` in a fully installed development environment (`pip install pytest` first for the one-command form `python -m pytest tests -q`):

```powershell
python tests/test_provider_status.py
python tests/test_pre_c_fixes.py
python tests/test_verdicts.py
python tests/test_eval_metrics.py
python tests/test_evidence.py
python tests/test_truthfulness.py
python tests/test_links_qr_privacy.py
python tests/test_pipeline_offline.py
python tests/test_api_chat.py
```

Then run `npm ci` and `npm run build` from `frontend/`. Some historical tests expect local test files that are intentionally not committed by `.gitignore`; provide only authorized test artifacts if a test requires them. Live provider tests can consume API quota and should be run deliberately, not as an unbounded loop.

### Validation performed on the final ZIP

Run in a clean environment: Python 3.12, `pip install -r backend/requirements.txt` plus `pytest`, Node with `npm ci`.

- **Passed:** full backend suite, `python -m pytest tests -q --ignore=tests/test_threat_intel_live.py` — **102 passed**. This includes provider status, evidence ledger, truthfulness, link/QR/privacy, verdict threshold mirror, eval metrics, offline pipeline, attachment/image forensics, RAG, correlation and `/`, `/health`, `/ready`.
- **Fixed during validation:** `test_macro_behavior.py::test_clean_document_produces_no_false_positives` was stale (the macro scanner now also returns `parse_failed`); the test expectation was updated. No product code changed.
- **Passed:** `npm ci && npm run build` in `frontend/` (Vite production build succeeds; the only warning is a >500 kB bundle chunk).
- **Passed:** `python -m compileall -q backend`, `node --check extension/background.js`, `node --check extension/content.js`.
- **Passed:** in-process API smoke test (FastAPI TestClient, fake DB, no live providers): `/health` and `/ready` respond; a benign email scored 12 (`LIKELY LEGITIMATE`); a synthetic phishing email scored 75 (`LIKELY PHISHING`) with display-name and link-text mismatches surfaced; `evidence_report`, `provider_status` and `privacy_report` returned; `/investigations/{id}` returned the stored record; `source=quick_content_check` reported `input_mode: quick_content_check`, listed original headers as unavailable and set `evidence_state: high_risk_evidence` with explicit limitations.
- **Not verified:** live Gemini / VirusTotal / AbuseIPDB calls, Render/Vercel deployment behavior, live Gmail DOM behavior, the real `sentence_transformers` embedder (the hash fallback was used), and the committed XGBoost pickle's version compatibility (it loads, but with an upgrade warning from a newer XGBoost). Push, redeploy, then repeat the hosted smoke test.

---

## 11. Files most relevant to Workflow B

- `backend/verdicts.py` — canonical verdict policy.
- `backend/evidence.py` — deterministic evidence ledger and narrative report.
- `backend/pipeline.py` — orchestration, result persistence and provider-status integration.
- `backend/provider_status.py` — normalized per-provider status and summary.
- `backend/privacy.py` — URL privacy policy and privacy/data-flow reporting.
- `backend/email_parser/eml_parser.py` — MIME parsing and charset fallback.
- `backend/forensics/link_analysis.py` — link-text versus destination analysis.
- `backend/forensics/qr_trace.py` — QR status and decoded destination trace.
- `backend/threat_intel/` — bounded external enrichment and lookup status.
- `frontend/src/components/report/` — evidence narrative, privacy flow and provider-status panels.
- `frontend/src/context/InvestigationContext.jsx` — readiness polling and analysis state.
- `extension/background.js`, `extension/content.js` — hosted endpoint configuration and user-initiated Gmail quick-check workflow.

**Exit criterion for Workflow B:** all documented tests pass in a clean dependency-complete environment; the new frontend build succeeds; the hosted smoke tests are repeated after deployment; provider coverage remains truthful when providers fail or are intentionally skipped; and the team either closes the public API authorization issue or keeps the demo restricted to synthetic/non-sensitive data until it does. The dynamic sandbox is the separate Workstream A and does not replace any of these gates.
