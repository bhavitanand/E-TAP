"""
B10: decide what may leave E-TAP in an external lookup, and describe the data
flows of an analysis.

Why: VirusTotal documents that URLs queried through its API can enter a
dataset shared with its community, and says not to submit sensitive
indicators. A phishing link usually carries exactly the sort of value that must
not leak: the recipient's address, a reset or session token, a one-time code.
Hostnames inside a private network are also something the user would not want
published.

`plan_url_lookup(url)` returns one of three actions:

    full     the URL as-is is safe to look up (no query, fragment or secret-looking path)
    trimmed  look up scheme://host/path only; the query string and fragment are dropped
    skip     do not send anything; the link looks personal, secret or internal

The check is heuristic and deliberately conservative. A skipped lookup is shown
to the user as "not looked up for privacy", never as "clean".
"""
from __future__ import annotations

import ipaddress
import math
import re
from typing import Any, Optional
from urllib.parse import parse_qsl, unquote, urlsplit

# Query keys that name a secret or a person. Matched against whole tokens of
# the key (split on _ - . and camelCase), so "sid" matches but "inside" does not.
_SENSITIVE_KEY_TOKENS = frozenset({
    "token", "tok", "key", "apikey", "secret", "sig", "signature", "session", "sessionid",
    "sid", "auth", "authorization", "code", "otp", "pass", "password", "pwd", "reset",
    "jwt", "bearer", "ticket", "nonce", "state", "email", "mail", "user", "username",
    "uid", "userid", "recipient", "rcpt", "to", "login", "account", "acct", "hash",
    "cred", "credential", "csrf", "mfa",
})
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+(?:@|%40)[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", re.I)
_B64ISH_RE = re.compile(r"^[A-Za-z0-9+/_\-=]{20,}$")
_HEX_RE = re.compile(r"^[0-9a-fA-F]{16,}$")
_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
_PRIVATE_SUFFIXES = (".local", ".internal", ".lan", ".corp", ".home", ".intranet", ".localdomain")


def _key_tokens(key: str) -> set[str]:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", key)
    return {t for t in re.split(r"[^A-Za-z0-9]+", spaced.lower()) if t}


def _entropy(text: str) -> float:
    if not text:
        return 0.0
    counts: dict[str, int] = {}
    for ch in text:
        counts[ch] = counts.get(ch, 0) + 1
    n = len(text)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def _looks_like_secret_value(value: str) -> bool:
    v = unquote(value or "")
    if _EMAIL_RE.search(v):
        return True
    if _HEX_RE.match(v) or _UUID_RE.match(v):
        return True
    if _B64ISH_RE.match(v) and _entropy(v) >= 3.2:
        return True
    return False


def _token_like_path_segment(seg: str) -> bool:
    """Long random-looking segment. A hyphenated word slug is not one."""
    if len(seg) < 24:
        return False
    if _HEX_RE.match(seg) or _UUID_RE.match(seg):
        return True
    hyphen_ratio = (seg.count("-") + seg.count("_")) / len(seg)
    if hyphen_ratio > 0.08:  # words joined by - or _, like an article slug
        return False
    has_digit = any(c.isdigit() for c in seg)
    has_alpha = any(c.isalpha() for c in seg)
    return has_digit and has_alpha and _entropy(seg) >= 3.8


def _internal_host(host: str) -> bool:
    h = host.lower().rstrip(".")
    if not h:
        return True
    try:
        ip = ipaddress.ip_address(h)
        return not ip.is_global
    except ValueError:
        pass
    return "." not in h or h == "localhost" or h.endswith(_PRIVATE_SUFFIXES)


def sensitive_url_reasons(url: str) -> list[str]:
    """Machine-readable reasons a URL should not be sent out. Empty list = nothing found."""
    reasons: list[str] = []
    try:
        parts = urlsplit(url)
        host = parts.hostname or ""
    except ValueError:
        return ["unparseable_url"]

    if parts.username or parts.password:
        reasons.append("credentials_in_url")
    if _internal_host(host):
        reasons.append("internal_or_private_host")
    if _EMAIL_RE.search(unquote(url)):
        reasons.append("email_address_in_url")

    pairs = parse_qsl(parts.query, keep_blank_values=True)
    # Fragments are sometimes used like query strings (#token=...).
    if parts.fragment and "=" in parts.fragment:
        pairs += parse_qsl(parts.fragment, keep_blank_values=True)
    for key, value in pairs:
        if _key_tokens(key) & _SENSITIVE_KEY_TOKENS:
            reasons.append("sensitive_parameter_name")
            break
    for _, value in pairs:
        if _looks_like_secret_value(value):
            reasons.append("token_like_parameter_value")
            break

    for seg in (s for s in parts.path.split("/") if s):
        seg = unquote(seg)
        if _token_like_path_segment(seg):
            reasons.append("token_like_path_segment")
            break
    if parts.fragment and "=" not in parts.fragment and _looks_like_secret_value(parts.fragment):
        reasons.append("token_like_fragment")

    # stable, de-duplicated
    return list(dict.fromkeys(reasons))


def personalised_url(url: str) -> bool:
    """True if the URL appears to carry a recipient-specific or secret value."""
    return any(r != "internal_or_private_host" for r in sensitive_url_reasons(url))


def plan_url_lookup(url: str) -> dict[str, Any]:
    """Decide how (or whether) `url` may be sent to an external reputation service."""
    reasons = sensitive_url_reasons(url)
    if reasons:
        return {"action": "skip", "lookup_url": None, "reasons": reasons}
    try:
        parts = urlsplit(url)
    except ValueError:
        return {"action": "skip", "lookup_url": None, "reasons": ["unparseable_url"]}
    if parts.query or parts.fragment:
        trimmed = f"{parts.scheme}://{parts.netloc}{parts.path}"
        return {"action": "trimmed", "lookup_url": trimmed, "reasons": ["query_or_fragment_removed"]}
    return {"action": "full", "lookup_url": url, "reasons": []}


REASON_TEXT = {
    "credentials_in_url": "contains a username or password",
    "internal_or_private_host": "points at a private or internal host",
    "email_address_in_url": "contains an email address",
    "sensitive_parameter_name": "has a parameter that names a token, code or person",
    "token_like_parameter_value": "has a long random-looking value (likely a token or ID)",
    "token_like_path_segment": "has a long random-looking path segment (likely a token or ID)",
    "token_like_fragment": "has a long random-looking fragment",
    "unparseable_url": "could not be parsed",
    "query_or_fragment_removed": "query string and fragment were removed before lookup",
}


def _safe_display(url: str) -> str:
    try:
        p = urlsplit(url)
        host = p.hostname or ""
        shown = f"{p.scheme}://{host}{p.path}"
        if len(shown) > 80:
            shown = shown[:79] + "…"
        return shown + ("?…" if (p.query or p.fragment) else "")
    except ValueError:
        return "(unparseable link)"


def build_privacy_report(
    *,
    email: dict,
    iocs: dict,
    threat_intel: dict,
    provenance: dict,
    attachments: Optional[list] = None,
) -> dict:
    """
    Plain data describing where this analysis's content went. Built from what
    the code actually does; the UI renders it, it does not invent it.
    """
    live = (provenance or {}).get("threat_intel_mode") == "live"
    provider = (provenance or {}).get("assessment_provider") or ""
    skipped_by_triage = bool((provenance or {}).get("gemini_skipped_by_triage"))
    gemini_used = provider.startswith("gemini") or "gemini" in provider
    urls = [u for u in (iocs or {}).get("urls") or [] if u]

    plans = [(u, plan_url_lookup(u)) for u in urls]
    n_full = sum(1 for _, p in plans if p["action"] == "full")
    n_trim = sum(1 for _, p in plans if p["action"] == "trimmed")
    skipped = [
        {"url": _safe_display(u), "reasons": p["reasons"],
         "why": "; ".join(REASON_TEXT.get(r, r) for r in p["reasons"])}
        for u, p in plans if p["action"] == "skip"
    ]
    n_ips = len((iocs or {}).get("ips") or [])
    n_domains = len((iocs or {}).get("domains") or [])
    n_hashes = len((iocs or {}).get("hashes") or [])

    def ext(provider_id, name, sends, count, notes=None, status=None):
        return {
            "id": provider_id, "name": name,
            "status": status or ("sent" if live and count else ("off" if not live else "nothing_to_send")),
            "sends": sends, "count": count, "notes": notes or [],
        }

    flows = [
        {
            "id": "local_parsing", "name": "E-TAP backend (parsing and analysis)",
            "status": "always",
            "sends": ["the message you submitted (headers, body, attachments)"],
            "notes": ["Everything below starts from this. Parsing and header, link and attachment checks run on the E-TAP server."],
        },
        {
            "id": "mongodb", "name": "E-TAP database (MongoDB)",
            "status": "stored",
            "sends": ["subject, sender and recipient addresses, date",
                      "header, attachment and link analysis results (including text read from images by OCR)",
                      "the list of URLs, domains, IPs and file hashes found, with full URLs",
                      "the verdict and explanation"],
            "notes": ["The message body is not saved as its own field.",
                      "There is currently no delete or retention control for stored analyses."],
        },
        {
            "id": "gemini", "name": "Google Gemini (AI interpretation)",
            "status": ("sent" if gemini_used else ("skipped_by_triage" if skipped_by_triage else "off")),
            "sends": ["subject, sender, recipient and reply-to",
                      "message body text and HTML (personal numbers and email addresses are masked when parsed from .eml)",
                      "header, link and attachment findings",
                      "the full URL list, including query strings",
                      "text read from images by OCR"],
            "notes": ["The URL sanitising below applies to VirusTotal lookups only. URLs sent to Gemini are not trimmed."],
        },
        ext("virustotal_urls", "VirusTotal (URLs)",
            ["scheme, host and path only when a query string is present; the full URL otherwise"],
            n_full + n_trim,
            notes=["VirusTotal may add queried URLs to a dataset shared with its community."]),
        ext("virustotal_hashes", "VirusTotal (file hashes)", ["SHA-256 hash only; files are never uploaded"], n_hashes),
        ext("abuseipdb", "AbuseIPDB (IP addresses)", ["public IP addresses found in headers and links"], n_ips),
        ext("whois", "WHOIS (domains)", ["domain names found in the message"], n_domains),
    ]
    return {
        "schema_version": 1,
        "input_mode": (provenance or {}).get("input_mode"),
        "external_lookups_enabled": live,
        "flows": flows,
        "url_lookups": {
            "total_urls": len(urls),
            "sent_in_full": n_full if live else 0,
            "sent_trimmed": n_trim if live else 0,
            "skipped_for_privacy": skipped,
            "would_send_in_full": n_full, "would_send_trimmed": n_trim,
            "note": ("Lookups are off, so nothing was sent." if not live else
                     "Skipped links were not looked up. They are unknown, not clean."),
        },
        "caveats": [
            "Hosted analysis is not local processing: the message is sent to the E-TAP backend and, "
            "when AI interpretation is on, to Google Gemini.",
        ],
    }
