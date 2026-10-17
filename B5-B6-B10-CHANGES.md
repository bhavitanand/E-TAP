# Workstream B5 + B6 + B10: link text vs destination, QR trace, URL privacy

Scope: B5, B6, B10 backend and data. Workstream A untouched. No scoring or verdict thresholds changed (B2 baseline re-run: identical 13/15 FP, 2/9 FN).

## Verified here
- `python tests/test_links_qr_privacy.py` (14 new tests) passes. Also still passing: `test_verdicts`, `test_evidence`, `test_truthfulness`, `test_pipeline_offline`, `test_eval_metrics`, `test_threat_intel`, `test_attachment_forensics`, `test_image_forensics`, `test_correlation_demo`, `test_graph_diffusion`, `test_triage`, `test_rag`.
- QR decoding tested with real generated QR images (OpenCV decoder), including no-QR, unreadable image, benign and look-alike destinations.
- VirusTotal request path tested with the request function mocked: a token/email URL sends nothing; a URL with a plain query sends only scheme://host/path (decoded the base64 id to prove it).

## NOT verified
- Live VirusTotal, live Gemini, live Gmail extension.
- `/investigations/{id}` and `/analyze` through FastAPI (fastapi could not be installed here). `app.py` compiles; the change is three added keys. Please hit the endpoint once.
- Not run, fail for environment reasons unrelated to this change: `test_classifier` and `test_parse_any` (sample files are git-ignored), `test_macro_behavior` (oletools missing), `test_api_chat` (fastapi missing), `test_single_email` (needs an .eml path argument; not run).
- The `pyzbar` decoder (only OpenCV was available here).

## What changed

### B10: privacy (`backend/privacy.py`, new; `threat_intel/vt_lookup.py`)
- `plan_url_lookup(url)` returns `full`, `trimmed` (scheme://host/path only) or `skip`. Skips URLs with credentials, email addresses, sensitive parameter names (token, code, session, reset, email, uid ...), token-like values (hex, UUID, high-entropy base64), token-like path segments, private/internal hosts. Hyphenated word slugs and `inside=1` are not blocked.
- `check_url_reputation` applies it. Skipped lookups return `{"malicious": None, "status": "skipped_privacy", "privacy_reasons": [...]}`: unknown, never clean, never cached, and the URL is not echoed.
- Evidence ledger shows skipped lookups under "Not checked or unknown" with the reason.
- `privacy_report` (new block in `/analyze` and `/investigations/{id}`): data flows for the E-TAP backend, MongoDB, Gemini, VirusTotal URLs, VirusTotal hashes, AbuseIPDB and WHOIS, each with status (sent / off / skipped / stored), what is sent and counts; plus `url_lookups` listing links skipped for privacy (shown without query strings) and how many were sent in full or trimmed.

### B5: link text vs destination (`forensics/link_analysis.py`, new)
- Reads `<a href>` with the visible text (and `<img alt>`), flags: text shows a different site, text names a brand but the link goes elsewhere, `user@host` trick, look-alike or mixed-script domain, punycode, bare IP, shortener, odd port, `javascript:`/`data:` links, redirect-style parameters.
- Redirects are never followed. Each link carries `resolution.status = "not_resolved"`. A redirect parameter's target is labelled `inferred_target_host`. Nothing is fetched, so no SSRF surface was added.
- Evidence strength: strong for `user@host`, mixed-script domains, script links, or a text mismatch combined with a look-alike, bare IP or shortener. A mismatch on its own is weak with the hedge that tracking links do this legitimately. "Link text matched" is neutral and never lowers risk.
- No HTML body (text-only mail) shows "could not be compared" as not checked. Quick content checks keep the existing "not inspected" item.

### B6: QR trace (`forensics/qr_trace.py`, new; `image_forensics.py`, `attachment_forensics.py`)
- Image scans now report `qr_status`: `decoded`, `no_qr_found`, `decoder_unavailable`, `image_unreadable` or `scan_failed`, plus every decoded payload (URL or other). `qr_urls` is unchanged for existing consumers.
- `qr_trace` lists each image, its status and each decoded destination run through the same link checks, with a `personalised` marker for recipient-specific values.
- Evidence: a QR code is no longer a risk signal by itself. The generic "hidden QR code" flag and neutral QR item are replaced by destination-based items; a benign QR is neutral, a look-alike or personalised destination is risk. Undecodable images show as not checked. "Do not scan the QR code" advice now only appears when the destination is flagged.

### Pipeline / API
- `pipeline.py` computes `link_analysis`, `qr_trace` and `privacy_report`, persists them and returns them. `/investigations/{id}` returns them (null for older records; not rebuilt, since the HTML and images were never stored).

## Changed behaviour to be aware of
- `test_truthfulness` previously sent `?token=SECRET123` through the VT error path. That URL is now skipped before any request, so the test uses a non-sensitive URL (it still checks that errors do not echo the sent URL).
- Trimmed lookups ask VirusTotal about a shorter URL, which can return "no record" where the full URL had one.
- An image attachment with a QR still sets `suspicious` (forces Gemini review); only the evidence wording changed.

## Found while doing this (not changed)
1. **Gemini still receives full URLs** (with query strings) and the full body/HTML. The sanitising applies to VirusTotal only. The privacy report says so explicitly. Sanitising the Gemini context is a natural next step but changes what the model sees.
2. **MongoDB stores full URLs** (`ioc_analysis`, and as keys in `threat_intel_analysis`). There is no delete/retention endpoint, which the privacy report states.
3. **Existing look-alike detection misses brand-plus-word domains**: `paypal-secure.com`, `hdfcbank-verify.com` (the module's own docstring example) and `secure-paypal-login.com` all return no match. Only near-spellings (`paypa1.com`) are caught. Not changed here.
4. JSON-sourced or `.msg` messages skip the `.eml` PII masking, so the "personal numbers and emails are masked" line in the Gemini flow only holds for `.eml` input.
5. Frontend: no dedicated privacy panel was built; the new evidence items appear in the existing evidence view automatically, and `privacy_report` is returned for a panel to render.
