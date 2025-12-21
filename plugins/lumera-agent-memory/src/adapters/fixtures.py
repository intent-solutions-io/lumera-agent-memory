"""Test fixtures for CASS memory system (used when cm CLI not available)."""

FIXTURE_SESSIONS = {
    "test-session-001": {
        "session_id": "test-session-001",
        "timestamp": "2025-12-20T10:00:00Z",
        "tool_name": "baseline-forecaster",
        "success": True,
        "summary": "Ran M4 baseline forecast with AutoETS and AutoTheta models",
        "tags": ["baseline", "m4", "statsforecast", "test"],
    },
    "test-session-002": {
        "session_id": "test-session-002",
        "timestamp": "2025-12-20T11:30:00Z",
        "tool_name": "bigquery-sync",
        "success": True,
        "summary": "Synced forecast results to BigQuery dataset",
        "tags": ["bigquery", "sync", "test"],
    },
    "test-session-003": {
        "session_id": "test-session-003",
        "timestamp": "2025-12-20T14:15:00Z",
        "tool_name": "timegpt-forecast",
        "success": False,
        "summary": "TimeGPT API request failed due to rate limit",
        "tags": ["timegpt", "api-error", "test"],
    },
}


def get_fixture_session(session_id: str):
    """Get fixture session data.

    Args:
        session_id: Session ID to retrieve

    Returns:
        Session dict or None if not found
    """
    return FIXTURE_SESSIONS.get(session_id)
