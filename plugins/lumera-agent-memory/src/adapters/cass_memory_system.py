"""Adapter for Jeff Emanuel's CASS memory system.

Integrates with `cm` CLI when available, falls back to fixtures in CI.
"""

import json
import shutil
import subprocess
from typing import Dict, Any, Optional
from .fixtures import get_fixture_session


class CASSAdapter:
    """Adapter for CASS memory system CLI."""

    def __init__(self):
        """Initialize adapter with capability detection."""
        self.cm_available = self._detect_cm_cli()

    def _detect_cm_cli(self) -> bool:
        """Check if cm CLI is available in PATH.

        Returns:
            True if cm binary found
        """
        return shutil.which("cm") is not None

    def export_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Export session data from CASS.

        Args:
            session_id: Session ID to export

        Returns:
            Session dict with keys: session_id, timestamp, summary, tags, etc.
            None if session not found

        Raises:
            RuntimeError: If cm CLI fails
        """
        if self.cm_available:
            return self._export_via_cm_cli(session_id)
        else:
            return self._export_via_fixture(session_id)

    def _export_via_cm_cli(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Export session using cm CLI.

        Args:
            session_id: Session ID to export

        Returns:
            Parsed JSON output from cm context --json
        """
        try:
            result = subprocess.run(
                ["cm", "context", session_id, "--json"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

            if result.returncode != 0:
                # Session not found or cm error
                return None

            data = json.loads(result.stdout)

            # Transform cm output to our schema
            # NOTE: Adjust field mapping based on actual cm output structure
            return {
                "session_id": session_id,
                "timestamp": data.get("timestamp", ""),
                "tool_name": data.get("tool", "unknown"),
                "success": data.get("success", True),
                "summary": data.get("summary", ""),
                "tags": data.get("tags", []),
            }

        except subprocess.TimeoutExpired:
            raise RuntimeError(f"cm CLI timeout for session: {session_id}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"cm CLI returned invalid JSON: {e}")
        except Exception as e:
            raise RuntimeError(f"cm CLI failed: {e}")

    def _export_via_fixture(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Export session using test fixture.

        Args:
            session_id: Session ID to export

        Returns:
            Fixture data or None if not found
        """
        return get_fixture_session(session_id)

    def is_cm_available(self) -> bool:
        """Check if cm CLI is available.

        Returns:
            True if cm can be used
        """
        return self.cm_available
