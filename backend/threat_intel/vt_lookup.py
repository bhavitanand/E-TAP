"""
URL and file-hash reputation via VirusTotal API v3.

VirusTotal's free tier is the tightest constraint in Stage E:
4 requests/min, 500/day. This module leans hard on TTLCache to avoid
burning quota on repeat lookups, and treats HTTP 429 (rate limited) as
a normal, expected outcome to report gracefully -- not a crash.

Caching rule: only DEFINITIVE answers are cached (a verdict from VirusTotal,
or "VirusTotal has never seen this"). Errors, timeouts, rate limits and
missing keys are never cached -- otherwise one transient failure would be
served back as "the answer" for the next hour.
"""

from __future__ import annotations
import os
import base64
import time
from collections import deque
import requests

from .cache import TTLCache

_vt_cache = TTLCache(ttl_seconds=3600)

VT_BASE_URL = "https://www.virustotal.com/api/v3"


class VirusTotalRateLimiter:
    """
    Sliding window throttle for VirusTotal's strict public API limit:
    4 requests per minute, 500 requests per day.
    Prevents API lockout (HTTP 429) across concurrent demo calls.
    """
    def __init__(self, max_requests_per_minute: int = 4):
        self.max_rpm = max_requests_per_minute
        self.request_timestamps: deque[float] = deque()

    def can_request(self) -> bool:
        now = time.monotonic()
        while self.request_timestamps and now - self.request_timestamps[0] > 60.0:
            self.request_timestamps.popleft()
        return len(self.request_timestamps) < self.max_rpm

    def record_request(self) -> None:
        self.request_timestamps.append(time.monotonic())


# NOTE: _vt_limiter uses process-local in-memory state and will under-protect the real quota if the backend is ever run with multiple Uvicorn workers (use Redis or an external distributed lock for multi-worker setups).
_vt_limiter = VirusTotalRateLimiter(max_requests_per_minute=4)


def _get_vt_key() -> str | None:
    return os.getenv("VIRUSTOTAL_API_KEY")


def _vt_headers() -> dict:
    return {"x-apikey": _get_vt_key(), "Accept": "application/json"}


def _url_to_vt_id(url: str) -> str:
    """VirusTotal identifies URLs by the base64 of the URL, no padding."""
    return base64.urlsafe_b64encode(url.encode()).decode().strip("=")


def _unavailable(reason: str, status: str = "error") -> dict:
    """
    A lookup that did not produce an answer. `malicious` is None (unknown),
    never False, so callers cannot mistake "could not check" for "clean".
    These results are deliberately NOT cached.
    """
    return {"malicious": None, "status": status, "error": reason}


def _vt_lookup(cache_key: str, path: str) -> dict:
    cached = _vt_cache.get(cache_key)
    if cached is not None:
        return cached

    if not _get_vt_key():
        return _unavailable("VIRUSTOTAL_API_KEY not set", status="not_configured")

    # Internal throttle: protect the 4 req/min free-tier quota
    if not _vt_limiter.can_request():
        return _unavailable(
            "VirusTotal free-tier quota (4 req/min) active — remote query throttled to prevent API lockout",
            status="rate_limited_internal",
        )

    try:
        _vt_limiter.record_request()
        response = requests.get(
            f"{VT_BASE_URL}/{path}",
            headers=_vt_headers(),
            timeout=10,
        )

        if response.status_code == 429:
            return _unavailable(
                "VirusTotal rate limit hit (4/min, 500/day on free tier)",
                status="rate_limited",
            )

        if response.status_code == 404:
            # Not previously seen by VT -- not necessarily benign, just unknown.
            # Submitting it for a fresh scan costs another quota unit, so we
            # report "unknown" rather than auto-submitting. This IS a
            # definitive answer, so it is cached.
            result = {"malicious": None, "status": "not previously scanned by VirusTotal"}
            _vt_cache.set(cache_key, result)
            return result

        response.raise_for_status()
        stats = response.json()["data"]["attributes"]["last_analysis_stats"]
    except (requests.RequestException, KeyError, TypeError, ValueError) as exc:
        # Do not echo the exception text: requests errors embed the full
        # request URL, which for url lookups contains the base64 of the
        # (possibly sensitive) link being checked.
        return _unavailable(f"VirusTotal request failed ({type(exc).__name__})")

    malicious_count = stats.get("malicious", 0) + stats.get("suspicious", 0)
    result = {
        "malicious": malicious_count > 0,
        "malicious_engine_count": malicious_count,
        "total_engines": sum(stats.values()),
        "stats": stats,
    }
    _vt_cache.set(cache_key, result)
    return result


def check_url_reputation(url: str) -> dict:
    return _vt_lookup(f"vt_url:{url}", f"urls/{_url_to_vt_id(url)}")


def check_hash_reputation(file_hash: str) -> dict:
    return _vt_lookup(f"vt_hash:{file_hash}", f"files/{file_hash}")
