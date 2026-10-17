# FastAPI Backend

The backend exposes the E-TAP forensic pipeline through `backend/app.py`. It accepts email artifacts, returns a structured investigation report, persists correlation-relevant analysis to MongoDB, and offers a SOC Assistant endpoint.

## Analysis flow

```text
.eml / .msg upload
  -> Stage A: parse and normalize message
  -> Stage B: header/authentication and received-chain analysis
  -> Stage B2: attachment type/hash/macro/image/QR/OCR analysis
  -> Stage D: IOC extraction
  -> Stage E: optional external threat-intelligence lookups
  -> Stage F: historical IOC/campaign correlation and persistence
  -> Stage C': XGBoost metadata triage when model is available
  -> Stage G: Gemini-assisted final assessment (unless safe triage skips it)
  -> Stage H: response assembly and background RAG summary/embedding persistence
```

The heuristic guard can force Stage G when selected risky keywords or URLs are present. The bundled XGBoost model is a triage aid; its model quality is not a substitute for validation on representative real-world mail. If the model cannot load, the pipeline continues without triage.

## Forensic modules

- `email_parser/` parses `.eml`, `.msg`, and related normalized structures.
- `forensics/header_forensics.py`, `auth_results.py`, `received_chain.py` inspect available headers and authentication evidence.
- `forensics/attachment_forensics.py`, `macro_scan.py`, `file_signatures.py`, and `image_forensics.py` inspect supported attachment artifacts. Macro analysis is static; attachments are not dynamically detonated.
- `forensics/ioc_extraction.py` extracts IOCs and relevant provenance.
- `threat_intel/` provides optional external reputation/WHOIS/geolocation lookups.
- `correlation/` correlates indicators and assigns/merges campaigns.
- `ai_engine/` performs metadata triage and optional Gemini assessment/MITRE-oriented explanation.
- `rag/` builds investigation summaries, embeds them, retrieves historical cases, and generates chatbot answers.
- `db/` manages the MongoDB handle, collection names, indexes and repository functions.

The Dockerfile installs Tesseract OCR and `libzbar` at the OS level. If these tools are not available in a non-Docker local environment, OCR/QR capabilities may be unavailable or degrade gracefully. `python-magic` is optional and is not listed in `backend/requirements.txt`; the signature detector includes a fallback signature table.

## Configuration

Use the repository-root `.env.example` as a template. The backend loads environment variables from the environment and, when present, `.env`:

```dotenv
MONGODB_URI=mongodb://localhost:27017/etap
MONGO_DB_NAME=etap
USE_FAKE_DB=0
AUTO_FALLBACK_DB=0
THREAT_INTEL_LIVE=0
ABUSEIPDB_API_KEY=
VIRUSTOTAL_API_KEY=
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.5-flash-lite
ALLOWED_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
PORT=5000
```

`USE_FAKE_DB=1` selects an in-memory test database that is not persistent. With `USE_FAKE_DB=0`, configure a real MongoDB URI and confirm the startup log says the connection succeeded. `THREAT_INTEL_LIVE=0` disables live threat-intelligence lookup; set it to `1` only after reviewing the data sent to providers. Gemini behavior depends on `GEMINI_API_KEY` and the configured model being available to that API key.

## Start locally

From the repository root:

```powershell
.\.venv\Scripts\Activate.ps1
cd backend
python -m uvicorn app:app --reload --host 127.0.0.1 --port 5000
```

API: <http://127.0.0.1:5000>. Health: <http://127.0.0.1:5000/health>. Interactive docs: <http://127.0.0.1:5000/docs>.

## API endpoints

### `POST /analyze`

Accepts multipart form data with a `file` field containing an `.eml` or `.msg` artifact. The maximum upload size is 25 MB. The response is a JSON report containing the email metadata, risk/verdict, header/attachment findings, IOCs, threat intelligence, correlation details, AI assessment and stage status. Exact fields depend on parser output and which analysis stages ran.

Example from PowerShell (run from the repository root, changing the path):

```powershell
curl.exe -X POST "http://127.0.0.1:5000/analyze" -F "file=@C:\path\to\suspicious.eml"
```

### `POST /chat`

JSON body supports `question` (required) and optional `email_id` / `email_context`. With active report context it answers about that artifact; otherwise it retrieves relevant stored investigations and asks Gemini to answer from that evidence. If Gemini fails, the handler can return a structured local summary instead.

### `GET /investigations/{email_id}`

Fetches an individual persisted investigation. This is not a list endpoint; the browser History tab currently keeps its list in local storage.

### `GET /health`

Returns `{"status":"ok"}` if the API responds. It does not perform a database health check.

## CLI

Run the pipeline directly from the `backend/` directory:

```powershell
python run_pipeline.py C:\path\to\suspicious.eml
```

For a local offline test without MongoDB or external keys, set these environment variables for the current PowerShell session before running a relevant test:

```powershell
$env:USE_FAKE_DB = "1"
$env:THREAT_INTEL_LIVE = "0"
python tests/test_pipeline_offline.py
```

## RAG behavior and limitations

Historical search uses cosine similarity over MongoDB investigation summaries by default. `sentence-transformers` is optional and is not part of `requirements.txt`; on Render, the code intentionally uses a deterministic hash-based 384-dimensional fallback embedder to reduce memory usage. This supports a runnable demo but is not equivalent to a trained semantic embedding model. Atlas Vector Search is optional and requires a matching index configured before `USE_ATLAS_VECTOR_SEARCH=1` is enabled.
