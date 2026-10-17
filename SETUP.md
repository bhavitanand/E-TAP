# E-TAP — Local Setup

## Prerequisites

- Python 3.11 recommended (the Docker image uses Python 3.11).
- Node.js 20+ and npm.
- Optional: MongoDB Community Server for local persistence, with MongoDB Compass as the GUI.
- Optional: provider API keys for live threat-intelligence and Gemini analysis.

## 1. Configure environment

From the repository root:

```powershell
Copy-Item .env.example .env
```

Edit `.env`. For an initial smoke test, set `USE_FAKE_DB=1`, `THREAT_INTEL_LIVE=0`, and leave external API keys empty. Fake DB data is not persistent.

## 2. Start the backend

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
cd backend
python -m uvicorn app:app --host 127.0.0.1 --port 5000
```

Verify `http://127.0.0.1:5000/health` returns a JSON status.

## 3. Start the frontend

In a second terminal from the repository root:

```powershell
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173`. The Vite development proxy forwards API requests to `127.0.0.1:5000`.

## 4. Connect MongoDB Compass

Compass is a client; a MongoDB server must be running separately.

- Local: install/start MongoDB Community Server and connect Compass to `mongodb://localhost:27017`.
- Atlas: create a cluster and database user, then set `MONGODB_URI` to the Atlas connection string.

Set `MONGO_DB_NAME=etap`. If the URI includes a database name, ensure it matches the intended database. Encode reserved characters in the password (for example `@` as `%40`). Do not paste connection strings into source files, screenshots, or GitHub issues.

## 5. Add fresh provider API keys

Create fresh keys under your own accounts. Store them in `.env` locally and as secret environment variables on Render (never in frontend variables). Enable `THREAT_INTEL_LIVE=1` only after confirming the relevant code paths and data-sharing behavior. Empty keys / disabled live lookups should be the first test configuration.

## 6. Load the Gmail extension (experimental)

1. Start the local backend.
2. Go to `chrome://extensions`, enable Developer mode, and select **Load unpacked**.
3. Choose the `extension` folder.
4. Open a test Gmail mailbox and test with harmless sample messages first.

The extension is a prototype: it scrapes visible Gmail content, reconstructs a simplified email, and sends it to the configured API. It cannot reliably inspect all original headers/authentication data. Configure the API and dashboard URLs in `extension/background.js` and `extension/content.js` respectively. Update host permissions in `extension/manifest.json` for the hosts you use. Use a dedicated test account and never assume message content remains on-device.

## Troubleshooting

- **Backend won't start:** activate `.venv`, install `backend/requirements.txt`, then run Uvicorn from `backend/`.
- **MongoDB connection error:** confirm the service is running, URI/user/password are correct, and Atlas network access permits the backend.
- **CORS error in browser:** set `ALLOWED_ORIGINS` to the exact frontend origin, restart the backend, and avoid wildcard origins in production.
- **Frontend shows API offline:** confirm `/health` responds and that the frontend is opened at the Vite URL.
- **External lookups fail:** first set `THREAT_INTEL_LIVE=0`; verify local parsing works before troubleshooting keys/rate limits.
