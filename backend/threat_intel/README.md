# Threat Intelligence Lookups (Stage E)

The `threat_intel/` package optionally enriches IOCs extracted by Stage D. Live lookups are controlled by `THREAT_INTEL_LIVE`; provider failures are represented as per-indicator errors/statuses where possible so one unavailable lookup does not necessarily abort the whole analysis.

## Providers used

| Indicator | Provider / method | Environment variable |
|---|---|---|
| Public IP reputation | AbuseIPDB | `ABUSEIPDB_API_KEY` |
| IP geolocation | ip-api.com batch API | No key in the current implementation |
| Domain age and registrar | WHOIS via `python-whois` | No API key in the current implementation |
| URL and file-hash reputation | VirusTotal API v3 | `VIRUSTOTAL_API_KEY` |

Private, loopback and reserved IP addresses are skipped for external IP reputation/geolocation lookups. This helps avoid sending internal addresses to public services.

## Configuration

```dotenv
THREAT_INTEL_LIVE=0
THREAT_INTEL_MAX_LOOKUPS_PER_PROVIDER=2
ABUSEIPDB_API_KEY=
VIRUSTOTAL_API_KEY=
```

Keep `THREAT_INTEL_LIVE=0` when testing offline parsing. Set it to `1` to enable implemented live lookups after adding valid provider keys and reviewing privacy implications. Third-party lookups transmit IOCs (such as public IPs, URLs and file hashes) to the provider; domain WHOIS and geolocation requests also require outbound network access.

Store keys in the repository-root `.env` for local development or in the backend service's secret environment settings for hosting. Never place them in the frontend bundle or commit them.

## Result behavior

The stage produces structured results including lookup mode, IP reputation, domain information, URL/file-hash reputation and geolocation data where applicable. Exact fields vary by provider response and error state.

- Missing key: returns an error/status for the affected lookup rather than treating the indicator as clean.
- Unknown indicator (for example, a VirusTotal 404 for an unscanned URL/hash): remains unknown; it is not equivalent to a confirmed benign result.
- Rate limits and network/WHOIS failures are reported and the relevant lookup is degraded gracefully where supported.
- Short-lived in-memory caches reduce duplicate requests during a running backend process; cache contents do not survive a process restart.

Provider quotas and terms change; consult each provider's current plan before running repeated live tests. VirusTotal requests are throttled in-process by this implementation, but a process-local limiter is not a distributed quota controller across multiple backend instances.

B11 adds a normalized per-provider status summary in the analysis report. A timeout, quota limit, missing key, disabled provider, no-record response and privacy/policy skip are distinct states. Missing or skipped lookup results remain unknown and must not be displayed as benign. `THREAT_INTEL_MAX_LOOKUPS_PER_PROVIDER` is clamped to 1–20 and defaults to 2; VirusTotal URL and hash queries share its per-analysis budget. Provider availability is separate from the threat verdict.

## Modules and tests

- `cache.py` — in-memory TTL cache.
- `ip_lookup.py` — AbuseIPDB reputation and IP geolocation.
- `domain_lookup.py` — WHOIS domain age/registrar lookup.
- `vt_lookup.py` — VirusTotal URL/hash reputation.
- `threat_intel.py` — `enrich_iocs()` orchestration entry point.
- `../tests/test_threat_intel.py` — mocked responses; no real provider calls required.
- `../tests/test_threat_intel_live.py` — real-network integration test; requires valid API keys and may consume provider quota.

Run the mocked test from `backend/` with your project's test runner. Do not run live tests repeatedly against large datasets; use a small, non-sensitive test artifact and monitor quota.
