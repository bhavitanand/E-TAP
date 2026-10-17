# E-TAP — Deployment Guide

Deploy the API and static frontend separately. Keep secrets on the backend only.

## Architecture

```text
Browser → Vercel (React/Vite static frontend)
        → Render (FastAPI backend)
        → MongoDB Atlas
        → Optional Gemini / VirusTotal / AbuseIPDB APIs
```

## 1. MongoDB Atlas

1. Create a cluster and a dedicated database user with access only to the E-TAP database.
2. Copy the application connection string and set the database to `etap`.
3. Configure Atlas Network Access for the backend host. Render's outbound IPs can vary by plan/region; use the narrowest workable rule and review it after deployment.
4. Store the URI as a secret environment variable, never in the repository.

## 2. Deploy the backend to Render

- Create a **Web Service** connected to this repository.
- Root Directory: `backend`
- Runtime: Docker (recommended, as `backend/Dockerfile` installs OCR/QR system libraries), or Python if you have validated all native dependencies.
- Dockerfile Path: `backend/Dockerfile` if the service root is repository root; if Root Directory is `backend`, use `Dockerfile`.
- Health Check Path: `/health`
- Set environment variables in Render:
  - `MONGODB_URI` = Atlas connection string
  - `MONGO_DB_NAME=etap`
  - `USE_FAKE_DB=0`
  - `AUTO_FALLBACK_DB=0`
  - `THREAT_INTEL_LIVE=0` initially
  - `GEMINI_API_KEY`, `VIRUSTOTAL_API_KEY`, `ABUSEIPDB_API_KEY` only if used
  - `ALLOWED_ORIGINS=https://YOUR-FRONTEND.vercel.app`
- Start command for a Python runtime: `uvicorn app:app --host 0.0.0.0 --port $PORT`. The provided Dockerfile currently uses port 5000; for a Render Docker deployment, confirm the service's port configuration or update the Docker command to consume `$PORT`.

Test `https://YOUR-BACKEND.onrender.com/health` before deploying the frontend.

## 3. Deploy frontend to Vercel

- Import the repository into Vercel.
- Root Directory: `frontend`
- Framework: Vite
- Build command: `npm run build`
- Output directory: `dist`
- Set `VITE_API_BASE_URL=https://YOUR-BACKEND.onrender.com` only if the frontend API client reads this variable. Check `frontend/src/api/analyze.js`; if it currently uses relative URLs, configure the API base there and rebuild.
- Set the exact Vercel origin in backend `ALLOWED_ORIGINS`, then redeploy/restart the backend.

## 4. Production safety checklist

- Never commit `.env`, API keys, database URIs, or user tokens.
- Keep external integrations disabled until their data-sharing implications are understood.
- Use a least-privilege MongoDB database user and rotate credentials if they were previously shared.
- Avoid wildcard CORS and broad network access when narrower configuration works.
- Configure upload limits, rate limits, logs, and provider quotas; monitor Render logs during testing.
- The Gmail extension is experimental and is not ready for general release or real sensitive inboxes.
- Do not advertise the app as a Gmail replacement, a guaranteed detector, or fully local-only.
