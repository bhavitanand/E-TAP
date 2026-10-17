# E-TAP — Current Work Plan

## Product goal

E-TAP (Email-TAP) bridges the gap between technical email-forensics evidence and understandable, actionable guidance for everyday users, while retaining a deeper investigation view for security practitioners.

## Current phase: stabilize the existing web application

- [ ] Verify local backend startup and `/health`.
- [ ] Verify frontend install/build and backend connectivity.
- [ ] Run parser and forensic tests against the small committed fixtures.
- [ ] Configure a fresh MongoDB database and validate persistence.
- [ ] Add fresh API keys only after local-only / no-key mode works.
- [ ] Validate each external API integration, rate limits, and what data is transmitted.
- [ ] Deploy backend and frontend separately; configure exact CORS origins and environment variables.
- [ ] Re-test the Gmail browser extension against a dedicated test mailbox.

## Known issues / risks to validate

1. **Gmail extension is experimental.** It scrapes the rendered Gmail DOM, then reconstructs a simplified message. It does not reliably preserve the raw message or complete authentication headers, and Gmail's selectors can change.
2. **External data sharing.** Live reputation services and generative AI providers may receive indicators or message-derived data. Make this explicit; do not claim full local-only processing while using cloud APIs.
3. **Extension API URL.** `extension/background.js` points to the API base URL; `extension/content.js` points to the dashboard. Update both for a hosted deployment and ensure `extension/manifest.json` permits the API host.
4. **CORS.** Set `ALLOWED_ORIGINS` to exact frontend origins on the backend host.
5. **MongoDB.** `USE_FAKE_DB=1` is ephemeral and only for smoke tests. Use a real local MongoDB server or Atlas for persistence.
6. **Secrets.** Keep API keys and database credentials in `.env` locally and secret environment variables in hosting providers. Never commit them.
7. **Detection quality.** Risk scores are triage, not proof. Validate false positives/negatives with benign and malicious test messages.

## Later phase: Tauri desktop shell

After the existing website and backend are stable, evaluate Tauri packaging. Keep the Python forensic engine as a managed local sidecar, and design secure lifecycle management and token storage before adding Gmail OAuth. Do not attempt full Gmail feature parity in the first iteration.

## Team

- Bhavit
- Krish Anand
- Yashmit Kamal
