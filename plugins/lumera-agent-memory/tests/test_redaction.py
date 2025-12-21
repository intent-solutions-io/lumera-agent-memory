"""Security tests for fail-closed redaction."""

import pytest
from src.security import redact_session, RedactionError


def test_redaction_passes_safe_data():
    """Safe data should pass redaction."""
    session = {
        "session_id": "test-001",
        "timestamp": "2025-12-20T10:00:00Z",
        "tool_name": "forecaster",
        "success": True,
        "summary": "Ran baseline forecast",
        "tags": ["test", "baseline"],
    }

    redacted = redact_session(session)
    assert redacted["session_id"] == "test-001"
    assert "summary" in redacted


def test_redaction_fails_on_api_key():
    """API key should trigger RedactionError."""
    session = {
        "session_id": "test-002",
        "summary": "Config with API_KEY=sk_1234567890abcdefghijklmnopqrs",
    }

    with pytest.raises(RedactionError, match="Secrets or PII detected"):
        redact_session(session)


def test_redaction_fails_on_aws_key():
    """AWS access key should trigger RedactionError."""
    session = {
        "session_id": "test-003",
        "summary": "AWS key: AKIAIOSFODNN7EXAMPLE",
    }

    with pytest.raises(RedactionError, match="Secrets or PII detected"):
        redact_session(session)


def test_redaction_fails_on_ssh_key():
    """SSH private key should trigger RedactionError."""
    session = {
        "session_id": "test-004",
        "summary": "-----BEGIN RSA PRIVATE KEY-----\\nMIIEowIBAAKCAQEA...",
    }

    with pytest.raises(RedactionError, match="Secrets or PII detected"):
        redact_session(session)


def test_redaction_fails_on_email():
    """Email (PII) should trigger RedactionError."""
    session = {
        "session_id": "test-005",
        "summary": "Contact user@example.com for details",
    }

    with pytest.raises(RedactionError, match="Secrets or PII detected"):
        redact_session(session)


def test_redaction_fails_on_credit_card():
    """Credit card number should trigger RedactionError."""
    session = {
        "session_id": "test-006",
        "summary": "Payment: 4111-1111-1111-1111",
    }

    with pytest.raises(RedactionError, match="Secrets or PII detected"):
        redact_session(session)


def test_redaction_requires_session_id():
    """Session ID is required field."""
    session = {"summary": "Missing session ID"}

    with pytest.raises(RedactionError, match="session_id is required"):
        redact_session(session)


def test_redaction_allowlist_only():
    """Only allowlisted fields should persist."""
    session = {
        "session_id": "test-007",
        "timestamp": "2025-12-20T10:00:00Z",
        "dangerous_field": "This should not persist",
        "api_response": {"nested": "data"},
    }

    redacted = redact_session(session)
    assert "dangerous_field" not in redacted
    assert "api_response" not in redacted
    assert redacted["session_id"] == "test-007"
