"""Fail-closed redaction layer for session data.

CRITICAL: This module implements a default-deny security posture.
If ANY secret or PII is detected, storage is aborted with RedactionError.
"""

import re
from typing import Any, Dict


class RedactionError(Exception):
    """Raised when secrets or PII detected in session data."""
    pass


# Secret detection patterns
PATTERNS = {
    "api_key": re.compile(r"(api[_-]?key|apikey)[=:]\s*['\"]?([a-zA-Z0-9]{32,})", re.IGNORECASE),
    "aws_access_key": re.compile(r"(AKIA[0-9A-Z]{16})"),
    "aws_secret_key": re.compile(r"(aws_secret|aws[_-]secret[_-]key)[=:]\s*['\"]?([a-zA-Z0-9/+=]{40})", re.IGNORECASE),
    "ssh_private_key": re.compile(r"-----BEGIN\s+(RSA|DSA|EC|OPENSSH)\s+PRIVATE KEY-----"),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "credit_card": re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"),
    "github_token": re.compile(r"gh[pousr]_[A-Za-z0-9_]{36,}"),
    "bearer_token": re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE),
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
}


def detect_secrets(data: Any) -> bool:
    """Recursively scan data structure for secrets.

    Args:
        data: Session data (dict, list, str, or primitive)

    Returns:
        True if ANY secret detected
    """
    if isinstance(data, dict):
        for value in data.values():
            if detect_secrets(value):
                return True
    elif isinstance(data, list):
        for item in data:
            if detect_secrets(item):
                return True
    elif isinstance(data, str):
        for pattern_name, pattern in PATTERNS.items():
            if pattern.search(data):
                return True
    return False


def redact_session(session: Dict[str, Any]) -> Dict[str, Any]:
    """Redact session data using fail-closed approach.

    Args:
        session: Raw session data dict

    Returns:
        Sanitized session dict with only allowlisted fields

    Raises:
        RedactionError: If secrets/PII detected
    """
    # Step 1: Detect secrets (fail-closed)
    if detect_secrets(session):
        raise RedactionError(
            "Secrets or PII detected in session data. "
            "Aborting storage. Please clean source data and retry."
        )

    # Step 2: Extract allowlisted fields only (default-deny)
    redacted = {}
    for field in ALLOWED_FIELDS:
        if field in session:
            redacted[field] = session[field]

    # Step 3: Ensure required fields present
    if "session_id" not in redacted:
        raise RedactionError("session_id is required but missing")

    return redacted
