# Correlation Engine and MongoDB Persistence

`correlation/engine.py` correlates the current email against previously analyzed emails, assigns/merges a campaign, and stores the analysis so subsequent investigations can compare against it.

## Flow

```text
Parsed email + forensic stages
        │
        ├── Stage D IOCs: IPs / domains / URLs / hashes
        ├── Optional Stage E reputation enrichment
        ▼
Stage F: historical correlation + campaign assignment
        ▼
MongoDB: analyzed_emails / campaigns / counters
```

## Matching and persistence

- Exact overlap for IPs, URLs and file hashes.
- Exact domain overlap plus fuzzy domain relationship checks using existing domain helpers.
- Returns related historical records and shared infrastructure details.
- Reuses an existing campaign for matching records, creates a campaign when appropriate, and merges campaigns when an artifact bridges groups.
- Stores correlation-relevant metadata and the stage results passed into the write path; the raw full email body is not intentionally saved by Stage F.
- When an existing `message_id` is present, the record is updated rather than duplicated, and the record is excluded from matching against itself.

Correlation is a heuristic relationship signal. A shared indicator does not by itself prove two emails share an actor or campaign.

## Database configuration

The engine uses the shared database handle from `db.connection`. Collections are named in `db/schema.py`:

- `analyzed_emails` — investigation records.
- `campaigns` — campaign membership and shared infrastructure.
- `counters` — sequence values used for readable campaign IDs.

For a local MongoDB server:

```dotenv
MONGODB_URI=mongodb://localhost:27017/etap
MONGO_DB_NAME=etap
USE_FAKE_DB=0
```

For Atlas, use the Atlas URI, keep the database name `etap`, and permit network access from the connecting host. `USE_FAKE_DB=1` selects an in-memory store for testing only; it is not persistent.

## Internal query helpers

`correlation/queries.py` exposes Python helper functions for recent analyses, time-window queries, IOC matches, campaigns, and campaign details. These helpers are not all exposed as HTTP API routes.

```python
queries.recent_analyses(limit=10)
queries.analyses_in_last_days(7)
queries.analyses_by_ioc("ips", "45.33.32.156")
queries.list_campaigns()
queries.campaign_detail("campaign_003")
```

## Tests and CLI

Run from the `backend/` directory. PowerShell example:

```powershell
$env:USE_FAKE_DB = "1"
$env:THREAT_INTEL_LIVE = "0"
python tests/test_correlation_demo.py
```

To run an end-to-end pipeline against a local artifact:

```powershell
$env:USE_FAKE_DB = "1"
$env:THREAT_INTEL_LIVE = "0"
python run_pipeline.py path\to\email.eml
```

Replace the path with an actual `.eml` file available on your machine. Raw email files are not included in this repository's test corpus.
