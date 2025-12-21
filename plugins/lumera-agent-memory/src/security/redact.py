"""Redaction layer with typed placeholders.

Security Model:
- CRITICAL secrets (private keys, auth headers): fail-closed (abort storage)
- NON-CRITICAL PII (emails, phones, tokens): redact with typed placeholders
- Always return redaction report showing what was redacted
"""

import re
from typing import Any, Dict, List, Tuple


class RedactionError(Exception):
    """Raised when CRITICAL secrets detected (fail-closed)."""
    pass


# Pattern definitions with criticality levels
CRITICAL_PATTERNS = {
    "ssh_private_key": re.compile(r"-----BEGIN\s+(RSA|DSA|EC|OPENSSH)\s+PRIVATE KEY-----"),
    "pgp_private_key": re.compile(r"-----BEGIN PGP PRIVATE KEY BLOCK-----"),
    "auth_header": re.compile(r"Authorization:\s*(Bearer|Basic)\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE),
}

REDACTABLE_PATTERNS = {
    "api_key": re.compile(r"(api[_-]?key|apikey)[=:]\s*['\"]?([a-zA-Z0-9]{32,})", re.IGNORECASE),
    "aws_access_key": re.compile(r"(AKIA[0-9A-Z]{16})"),
    "aws_secret_key": re.compile(r"(aws_secret|aws[_-]secret[_-]key)[=:]\s*['\"]?([a-zA-Z0-9/+=]{40})", re.IGNORECASE),
    "github_token": re.compile(r"gh[pousr]_[A-Za-z0-9_]{36,}"),
    "bearer_token": re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "credit_card": re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"),
    "phone": re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"),
    "ip_address": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "jwt": re.compile(r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),
}

# Allowlisted fields (default-deny: only these fields persist)
ALLOWED_FIELDS = {
    "session_id",
    "timestamp",
    "tool_name",
    "success",
    "summary",
    "tags",
    "schema_version",
    "metadata",
}


def detect_critical_secrets(data: Any) -> Tuple[bool, str]:
    """Scan for CRITICAL secrets (fail-closed).

    Args:
        data: Session data structure

    Returns:
        (found, pattern_name) tuple
    """
    if isinstance(data, dict):
        for value in data.values():
            found, pattern = detect_critical_secrets(value)
            if found:
                return found, pattern
    elif isinstance(data, list):
        for item in data:
            found, pattern = detect_critical_secrets(item)
            if found:
                return found, pattern
    elif isinstance(data, str):
        for pattern_name, pattern in CRITICAL_PATTERNS.items():
            if pattern.search(data):
                return True, pattern_name
    return False, ""


def redact_string(text: str, redaction_report: List[Dict]) -> str:
    """Redact PII/secrets from string with typed placeholders.

    Args:
        text: Input string
        redaction_report: List to append redaction events to

    Returns:
        Redacted string
    """
    redacted = text

    for pattern_name, pattern in REDACTABLE_PATTERNS.items():
        matches = pattern.findall(redacted)
        if matches:
            count = len(matches)
            redaction_report.append({"rule": pattern_name, "count": count})

            # Replace with typed placeholder
            placeholder = f"<REDACTED:{pattern_name.upper()}>"
            redacted = pattern.sub(placeholder, redacted)

    return redacted


def redact_data_structure(data: Any, redaction_report: List[Dict]) -> Any:
    """Recursively redact data structure.

    Args:
        data: Data structure (dict, list, str, or primitive)
        redaction_report: List to append redaction events to

    Returns:
        Redacted data structure
    """
    if isinstance(data, dict):
        return {k: redact_data_structure(v, redaction_report) for k, v in data.items()}
    elif isinstance(data, list):
        return [redact_data_structure(item, redaction_report) for item in data]
    elif isinstance(data, str):
        return redact_string(data, redaction_report)
    else:
        return data


def redact_session(session: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict]]:
    """Redact session data with typed placeholders.

    Args:
        session: Raw session data dict

    Returns:
        (redacted_session, redaction_report) tuple

    Raises:
        RedactionError: If CRITICAL secrets detected (fail-closed)
    """
    # Step 1: Detect critical secrets (FAIL-CLOSED)
    found, pattern = detect_critical_secrets(session)
    if found:
        raise RedactionError(
            f"CRITICAL secret detected ({pattern}). "
            "Aborting storage for security. Please remove secret from source data."
        )

    # Step 2: Redact non-critical PII with typed placeholders
    redaction_report = []
    redacted_data = redact_data_structure(session, redaction_report)

    # Step 3: Extract allowlisted fields only (default-deny)
    redacted = {}
    for field in ALLOWED_FIELDS:
        if field in redacted_data:
            redacted[field] = redacted_data[field]

    # Step 4: Ensure required fields present
    if "session_id" not in redacted:
        raise RedactionError("session_id is required but missing")

    return redacted, redaction_report
