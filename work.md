# E-TAP — Project Status and Work Plan

## Product goal

E-TAP (Email-TAP) bridges the gap between technical email-forensics evidence and understandable, actionable guidance for everyday users, while preserving detailed investigative information for security practitioners.

## Current status

The team has manually verified the local pipeline and deployed the current web application:

- [x] React/Vite dashboard loads locally and on Vercel.
- [x] FastAPI backend is deployed on Render and responds at `/health`.
- [x] Backend connects to the MongoDB Atlas `etap` database.
- [x] Live frontend's API base URL and backend CORS allowlist are configured for the current Vercel domain.
- [x] The built-in benign and phishing `.eml` test buttons were tested against the local pipeline; repeat tests against the hosted deployment when making backend/config changes.
- [x] Gemini and threat-intelligence keys are configured through backend environment settings, not frontend code.
- [ ] Re-test the complete hosted analysis → Atlas persistence → history/report retrieval → RAG Assistant flow after each material deployment change.
- [ ] Confirm the exact Gemini model configured for the deployment remains available to the team's API key.

Current URLs (update when changed):

- Frontend: <https://e-tap-lac.vercel.app/>
- Backend health: <https://etap-backend-od1c.onrender.com/health>
- API docs: <https://etap-backend-od1c.onrender.com/docs>

## Known limitations / risks

1. **Gmail extension is experimental.** It automatically inspects visible Gmail DOM elements, then reconstructs a simplified email message. It does not reliably preserve the original raw message, original authentication headers or attachments. The extension source currently targets localhost by default and must be pointed to the hosted URLs separately if required.
2. **Browser history is local.** The History page stores its list in browser `localStorage` (up to 50 entries). The backend persists individual analysis records in MongoDB, and exposes `GET /investigations/{email_id}`, but does not currently expose a general server-side history-list API.
3. **External data sharing.** Live reputation services can receive IOCs; Gemini prompts may include email-derived text and forensic evidence. Do not claim full local-only processing while using cloud APIs.
4. **RAG embedding quality.** On Render, the embedding code uses a deterministic hash-based fallback to reduce memory requirements. This is not the same as a trained semantic embedding model. Atlas Vector Search remains opt-in and requires a configured matching index.
5. **Detection quality.** Risk scores and campaign relationships are triage heuristics. Evaluate false positives and false negatives on diverse authorized samples before operational use.
6. **Secrets.** Keep API keys, database credentials and access tokens in `.env` locally or secret environment variables in hosting providers. Never commit them. Rotate any credential exposed in chat, screenshots, logs or repository history.
7. **Hosted runtime.** Render free instances may spin down and have limited CPU/RAM; large OCR, attachment analysis or multiple concurrent requests may be slow or exceed resource limits.

## Near-term priorities

- [ ] Add a health/readiness check that reports database connectivity separately from basic HTTP process health.
- [ ] Improve RAG retrieval quality and test evidence grounding on the hosted Atlas records.
- [ ] Fix stale dashboard copy that refers to local port 5000 in hosted mode.
- [ ] Audit Gmail extension permissions, consent, scan controls, authentication and hosted URL configuration before broader use.
- [ ] Decide whether a server-side paginated history endpoint is needed, instead of relying only on browser-local history.
- [ ] Run a documented clean-install test from a fresh clone and record the supported Python/Node versions.

## Later phase: Tauri desktop shell

After the web app, backend, privacy handling and extension are stable, evaluate a Tauri desktop shell. Keep the Python forensic engine as a managed local sidecar, and design secure process lifecycle management and token storage before adding Gmail OAuth. Full Gmail feature parity is outside the current MVP.

## Team

- Bhavit Anand
- Krish Anand
- Yashmit Kamal
