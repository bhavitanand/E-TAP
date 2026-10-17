# E-TAP (Email-TAP)

**The one-tap email forensics and protection platform** — bridging the gap between cybersecurity professionals and everyday email users.

E-TAP is a defensive email-artifact analysis application. The current version is a React/Vite dashboard backed by a Python/FastAPI analysis engine. It analyzes uploaded `.eml` and `.msg` files; it is **not yet a Gmail replacement or a full mail client**. The browser extension is an experimental Gmail overlay and should be treated as a prototype.

## Current capabilities

- Email parsing and MIME normalization for supported `.eml` / `.msg` artifacts.
- Header and authentication-related checks, received-chain inspection, and sender/domain analysis.
- Attachment and image analysis, including file-signature checks, QR extraction, and OCR where dependencies are available.
- Indicator-of-compromise extraction and optional threat-intelligence lookups.
- Optional Gemini-powered analysis and MITRE ATT&CK-oriented explanations.
- Campaign correlation and persistence through MongoDB.
- React dashboard, investigation history, and report views.

Feature availability depends on configuration and the specific artifact. Do not treat any automated verdict as definitive; verify evidence before taking action.

## Architecture

```text
React/Vite dashboard
       │ HTTP
       ▼
FastAPI API (backend/app.py)
       ├── email parsing + forensic pipeline
       ├── optional external threat-intelligence / AI APIs
       └── MongoDB (local or Atlas)
```

## Run locally (Windows PowerShell)

Requirements: Python 3.11 recommended, Node.js 20+ recommended, and optionally MongoDB Community Server or a MongoDB Atlas database.

1. Create the environment file:

   ```powershell
   Copy-Item .env.example .env
   ```

2. Edit `.env`. For a no-credentials smoke test, use `USE_FAKE_DB=1`, leave API keys empty, and set `THREAT_INTEL_LIVE=0`. The fake database is in-memory and is cleared when the backend exits.

3. Install Python dependencies and start the API:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r backend/requirements.txt
   cd backend
   uvicorn app:app --host 127.0.0.1 --port 5000
   ```

   In another terminal, from the repository root:

   ```powershell
   cd frontend
   npm ci
   npm run dev
   ```

4. Open `http://127.0.0.1:5173`. Check `http://127.0.0.1:5000/health` for API health.

If your shell does not allow virtual-environment activation, use `.venv\Scripts\python.exe -m pip ...` and `.venv\Scripts\python.exe -m uvicorn ...` instead.

## MongoDB: local Compass or Atlas

MongoDB Compass is a GUI client, not the database server. For local persistence, install/start MongoDB Community Server and connect Compass to `mongodb://localhost:27017`. Set `MONGODB_URI=mongodb://localhost:27017/etap` in `.env`.

For shared deployments, create a MongoDB Atlas cluster and a database user with only the required database permissions. Set `MONGODB_URI` to the Atlas connection string in the backend host's environment settings. Add the backend host's outbound network access as required by your Atlas configuration; avoid leaving `0.0.0.0/0` enabled permanently. Never commit `.env` or credentials.

## Fresh API keys

Create your own keys in the relevant provider consoles; do not reuse old team members' keys. Set them only in local `.env` or your hosting provider's secret/environment-variable panel:

- `GEMINI_API_KEY` — optional AI analysis.
- `VIRUSTOTAL_API_KEY` — optional domain/URL/file intelligence, subject to provider limits and terms.
- `ABUSEIPDB_API_KEY` — optional IP reputation lookup.
- `THREAT_INTEL_LIVE=1` — enables live lookups where supported by the implementation. Keep it `0` until keys and privacy behavior have been checked.

Live lookups may transmit indicators or related data to third-party providers. A local dashboard does **not** mean all analysis stays local.

## Gmail extension (experimental)

The extension currently scrapes visible Gmail DOM content and submits reconstructed plain-text email data to the configured E-TAP API. Gmail's DOM changes frequently, and this is not equivalent to parsing the original raw message or its full authentication headers. Test only with a dedicated test mailbox and non-sensitive sample messages.

1. Start the local backend.
2. Open `chrome://extensions`, enable Developer mode, choose **Load unpacked**, and select the `extension` folder.
3. Open Gmail and inspect the extension console / backend logs.
4. The extension API endpoint is configured in `extension/background.js`; the dashboard link is configured in `extension/content.js`. Change these when using hosted services, and ensure the target hosts are allowed in `extension/manifest.json`.

Do not deploy this prototype to real users until permissions, consent, data minimization, error handling, XSS safety, authentication, and provider policies have been reviewed. The extension sends email content to the configured backend for analysis.

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for a deployment checklist and [SETUP.md](SETUP.md) for expanded local setup. For a hackathon demo, deploy the backend separately from the static frontend and configure the frontend API base URL and CORS allowlist explicitly.

## Current limitations / next steps

- This is not a full Gmail replacement; Gmail OAuth/mailbox synchronization is not implemented.
- The extension uses Gmail DOM selectors that may break as Gmail changes.
- Live third-party APIs can send indicators/content-derived data outside the machine.
- The in-memory fake DB is for development only and is not persistent.
- Tauri packaging is a later milestone after the web app, backend configuration, and extension are stable.
- Automated detection can produce false positives and false negatives.

## Team

- the team
- Bhavit Anand
- Krish Anand
- Yashmit Kamal

## Project statement

E-TAP translates technical email-forensics findings into clear, evidence-backed explanations and practical next steps for ordinary users, while retaining deeper investigative detail for security practitioners.
