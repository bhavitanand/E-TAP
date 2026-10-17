# Workstream B-0 — truthfulness fixes

Scope: B-0 only. Dynamic sandbox (Workstream A) untouched.
Verified by: unit tests below + node check of `verdict.js` + syntax checks.
**Not verified:** full pipeline run, frontend build (no `node_modules`/network here), live Gmail DOM, live Render/Gemini/VT.

## What changed

| Item | Where | Behaviour now |
|---|---|---|
| Click-to-analyze | `extension/content.js`, `background.js` | No 2-second polling scan. A button is injected; text is read and sent only on click. Timeout (90 s), 429/5xx/network errors have user-facing messages and a retry button. "No result" is never shown as safe. |
| Quick Content Check | extension + `/analyze` `source` form field + `pipeline.py` + `forensics/header_forensics.py` | Extension sends `source=quick_content_check`. No invented `To:`/`Date:`. Backend skips Received/SPF/DKIM/DMARC (incl. the live-DNS fallback), reports them `not_available`, skips the XGBoost "safe" bypass and always does the content review. Report UI shows "Headers not available". |
| Stop caching VT errors | `threat_intel/vt_lookup.py` (+ `ip_lookup.py`, `domain_lookup.py`) | Only definitive answers are cached (verdict, or "VT never saw it"). 429, timeouts, bad responses, missing key are not. Failed lookups return `malicious: None`. Error text no longer embeds the looked-up URL. Same fix applied to AbuseIPDB, geo and WHOIS (WHOIS failures were cached 24 h). |
| One verdict policy | `backend/verdicts.py` | Labels: LIKELY LEGITIMATE / LOW RISK / SUSPICIOUS / LIKELY PHISHING / HIGH-RISK PHISHING at 0/20/40/65/85. Free-text labels ("Likely Malicious", …) are normalised. The more severe of label vs score wins, so a "legitimate" label can't sit next to a dangerous score. Backend sends `verdict_band`; clients render it. |
| Thresholds unified | web UI, PDF, history card, chat drawer, extension | Danger is now **≥65 everywhere** (web UI was ≥70, history card >60). Extension keeps no thresholds of its own. |
| Banner shows TI mode / provider / fallback | `analysis_provenance` in the report; `VerdictBanner.jsx`; extension banner | Chips: threat intel live / OFFLINE / N lookups unavailable; AI provider+model, offline fallback with scrubbed reason, or triage-only; label-adjusted note. |
| Debug prints removed | `pipeline.py` | Replaced with count-only `logger.debug`. No URLs, keywords or body text reach stdout/Render logs. |

Also: `analysis_provenance`, `stage_status`, `verdict_band` are now **persisted**, and `/investigations/{id}` returns them. Previously reopening a report via the extension's "View Full Report" link invented `E: live, G: gemini`; old records now show `unknown`. Raw Gemini exception text is no longer sent to clients (scrubbed copy only, in provenance). Triage-bypass explanation now states when external reputation lookups were not performed.

## Tests
```
cd backend
python tests/test_verdicts.py        # labels, thresholds, reconcile, JS-mirror drift check
python tests/test_truthfulness.py    # VT/AbuseIPDB error caching, header-unavailable mode
python tests/test_threat_intel.py    # existing; still passes
```

## Behaviour changes to be aware of
- Reports whose risk score is 65–69 now render as danger in the web UI (was caution).
- Final verdicts are uppercase canonical labels; stored mixed-case labels are normalised on read.
- Quick checks never take the "Gemini skipped" path, so they use more Gemini quota than before.

## Not done (intentionally, next)
- Extension still sends `innerText`: link targets and attachments are lost (B4/B5).
- `/investigations/{id}` and `/chat` are still unauthenticated (C5).
- VT still receives the full URL (B10 sanitisation).
- Provider-failure states beyond the TI count (B11).
