# Workstream B2: labelled eval set and FP/FN baseline

Scope: B2 only. No thresholds, rules or scoring were changed. Workstream A untouched.

## What was added
- `backend/eval/corpus.py`: loads a labelled corpus from folders (`*ham*` = benign, `*spam*` = malicious; `.json` ParsedEmail or `.eml`). Drops exact duplicates, skips and reports unlabelled folders.
- `backend/eval/metrics.py`: confusion, FPR/FNR, Wilson 95% intervals, read-only threshold sweep, per-category counts.
- `backend/eval/run_eval.py`: runs each message through the real `_run_parsed_pipeline` (fresh fake DB per message), writes `results.json` + `report.md`.
- `backend/tests/test_eval_metrics.py`: 6 tests for the maths and loader.
- `backend/eval/results/`: the baseline below.

Run: `cd backend && python -m eval.run_eval ../docs/extracted --out eval/results`
Production-like: `GEMINI_API_KEY=... python -m eval.run_eval CORPUS --use-gemini --live-threat-intel` (needs `xgboost`).

## Baseline (offline fallback configuration only)
24 unique messages (15 ham: 9 easy, 6 hard; 9 spam). Gemini off, XGBoost triage unavailable (not installed in the sandbox), threat intel offline.

| operating point | false positives | false negatives |
|---|---|---|
| band=danger (score >= 65) | 13/15 ham (87%, CI 62-96%) | 2/9 spam (22%, CI 6-55%) |
| band>=caution (score >= 40) | 13/15 | 2/9 |

Threshold sweep: identical from 40 to 65, so moving the thresholds inside that range changes nothing on this set.

## What the numbers actually say
1. **The offline fallback's verdict is essentially "contains a URL".** `stage_g._offline_content_classification` tags any text containing `http://`/`https://` as "Malicious Link / URL" (weight 85) -> "Likely Malicious" -> LIKELY PHISHING. Every ham that scored 70+ has URLs; the 2 ham that did not (no URLs) scored 10 and 20. This is the cause of the 13/15, not the thresholds.
2. **Both false negatives are parser failures, not detection misses.** `20030228_spam_2/00002...` and `00003...` have empty bodies: Stage A logged `Failed to decode single-part body: unknown encoding: DEFAULT`. The pipeline scored an empty message as LOW RISK / LIKELY LEGITIMATE. Two issues: the decode bug, and an empty body being rated safe instead of "could not analyse".
3. **This does not measure production.** Production has Gemini and (if the pickle loads) XGBoost triage; neither ran here. Re-run with `--use-gemini` before drawing conclusions about the hosted app. The fallback matters anyway: it is what users get when Gemini is down or over quota.
4. **The corpus is a poor fit for the product.** SpamAssassin is 2002-2005 spam, not phishing, and has no SPF/DKIM/DMARC results, so header analysis contributes almost nothing. "Malicious" here means spam. Hard-ham (legit newsletters/sweepstakes) is the useful FP probe.
5. **Too small to quote.** 24 messages; intervals above are wide. `docs/extracted/` holds only 3 files per folder, and `20050311_spam_2` is an exact copy of `20030228_spam_2` (dropped). Four "Re: New Sequences Window" messages are near-duplicates (kept).

## Not verified
- Any result with Gemini, XGBoost triage or live threat intel.
- `.eml` corpus loading against real files (only the `.json` path ran; the `.eml` branch is the existing `parse_email`).
- Existing tests re-run: `test_verdicts`, `test_evidence`, `test_truthfulness`, `test_pipeline_offline` pass. This sandbox needed a stub `extract_msg` (kept outside the repo; it is a hard import in `msg_parser.py` even for non-.msg input).

## Suggested next steps (not done, your call)
- Get the full SpamAssassin sets plus some phishing samples (for example the Nazario corpus) and some modern benign mail, then re-run. Aim for hundreds per class.
- Run `--use-gemini` with xgboost installed to get the production baseline.
- Fix the `DEFAULT` transfer-encoding decode in Stage A, and make an empty/undecodable body produce an "unavailable" evidence state instead of a low score.
- Only after that, decide whether the offline URL rule needs changing.
