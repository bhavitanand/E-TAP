# Workstream B1 + B9: evidence model and "observed / why it matters / what to do" report

Scope: B1 and B9 only. Dynamic sandbox (Workstream A) untouched.

## Verified here
- `python tests/test_evidence.py` (19 tests), plus the existing `test_verdicts`, `test_truthfulness`, `test_threat_intel`, `test_pipeline_offline` still pass.
- Full offline pipeline run in both modes (full message, quick content check); `/analyze` and `/investigations/{id}` exercised through FastAPI's TestClient, including rebuilding a record that has no stored `evidence_report`.
- `npm ci && npm run build` succeeds (this also closes the "frontend build not run" gap from B-0).
- `EvidenceNarrative` server-rendered with real payloads (full, quick, and missing/empty report).
- Extension banner `renderResult` run in jsdom with a new-style and an old-style (no `evidence_report`) response.

## NOT verified
- A live Gemini call. `ai_findings` is a new optional field in the response schema and the prompt changed. If Gemini rejects the schema or ignores the field, behaviour degrades safely (findings absent, falls back to the old `supporting_evidence` lines marked "not tied to specific evidence"), but run one real analysis and check `ai_analysis.final_assessment.ai_findings`.
- Live Gmail DOM, Render/Vercel, live VT/AbuseIPDB.
- The visual look of the new panel in a browser (only server-rendered markup was checked).

## What changed

### Evidence model (`backend/evidence.py`, new)
Every finding is an item with: `id`, `kind` (`observed` | `reputation` | `ai_inferred`), `status` (`present` | `absent` | `unavailable`), `direction` (`raises_risk` | `lowers_risk` | `neutral`), `weight` (`strong` | `weak`), `source`, `title`, `detail`, `why`.
- Observed and reputation items are built deterministically from parsed output. No model is involved.
- `unavailable` means not checked or the check failed. It never pushes the verdict either way and is listed under "Not checked or unknown". Offline threat intel, VT failures, VT "no record", private IPs, missing headers, and (for quick checks) attachments and link destinations all land here.
- A clean reputation result is only a weak "lowers risk" item with a hedge. A single low-count VT detection is weak; 3+ engines is strong. Auth "pass" is weak and says it does not show the content is safe.
- URLs shown in evidence have query strings and fragments removed.
- AI items must cite ledger ids. Ids that do not exist are dropped, and a statement with no valid citation is kept but labelled "Not tied to specific evidence" and can never become a headline reason.
- Offline-fallback output is not re-presented as independent evidence (its `supporting_evidence` just echoes the observed items).
- The report payload gains `evidence_report`: `conclusion` (label, band, `evidence_state`, `confidence_level`, `limitations`), `headline`, `top_reasons`, `contradicting`, `evidence`, `sections`, `ai_summary`, `what_to_do` (`steps` + `ai_suggestions`), `counts`.
- `evidence_state` is `high_risk_evidence`, `suspicious_uncertain` or `no_high_risk_found`. There is no "safe" state.
- `confidence_level` is capped when the verdict is not danger and there are limitations (quick check, offline TI, fallback).

### Pipeline / API
- `pipeline.py`: builds the ledger before Stage G, gives the model a compact copy as `evidence_ledger`, builds and persists `evidence_report`, returns it.
- `ai_engine/schemas.py`: new `AiFinding`; `FinalAssessment.ai_findings` (optional, default empty).
- `ai_engine/stage_g.py`: prompt now treats email content as untrusted data, asks for grounded `ai_findings`, and says unavailable checks are unknown, not clean. Model-failure logging no longer prints exception text (type only).
- `ai_engine/prompts.py`: untrusted-input paragraph added to the content prompt.
- `app.py`: `/investigations/{id}` returns the stored `evidence_report`, or rebuilds one for older records and marks it `reconstructed: true`.

### UI
- New `EvidenceNarrative.jsx` under the verdict banner: headline, "what this verdict could not take into account", then 1 **What we observed** (with source chips and a "Not checked or unknown" group), 2 **Why it matters** (top reasons with plain-language explanations, evidence pointing the other way, collapsed AI interpretation), 3 **What you should do**.
- "What to do" is fixed, conservative guidance by verdict band plus steps tied to specific evidence (do not open file X, do not scan the QR code, do not reply). It does not say a device is infected or that the user is safe. Gemini's suggested actions are shown separately, collapsed, labelled as AI.
- Verdict banner: shows the deterministic headline and "Evidence confidence: HIGH/MEDIUM/LOW" instead of the model's raw percentage when a report is present.
- Extension banner: headline, top reasons tagged Observed/Reputation/AI-inferred, a "Not checked" list, and the first next step. The green check for low-risk results is now an info icon with "No high-risk signals found in the visible text". Falls back to the old display against an older backend.

## Behaviour changes to be aware of
- The headline now comes from the evidence, not Gemini's free text. Gemini's explanation is still shown, under "AI interpretation".
- The Gemini prompt is longer (ledger added), so a little more input per call.
- "Evidence confidence" can read LOW for a low-risk verdict when headers/reputation were unavailable. That is intended.

## Not done (next)
- PDF export and the SOC chat drawer still use the old fields.
- Link text vs destination, QR trace (B5/B6), URL sanitisation before VT and the privacy panel (B10), provider-status states beyond counts (B11).
- `/investigations/{id}` and `/chat` are still unauthenticated (C5).
- No labelled evaluation yet: nothing here claims better detection accuracy (B2).
