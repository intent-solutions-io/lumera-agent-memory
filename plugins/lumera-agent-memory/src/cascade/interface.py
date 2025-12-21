"""Abstract interface for Cascade connector.

Designed for easy swap from MockCascadeConnector to LiveCascadeConnector.
"""

from abc import ABC, abstractmethod


class CascadeConnector(ABC):
    """Abstract base class for Cascade storage connectors."""

    @abstractmethod
    def put(self, data: bytes) -> str:
        """Store blob in Cascade, return content-addressed pointer.

        Args:
            data: Encrypted blob bytes

        Returns:
            Pointer in format: cascade://<content-hash>
        """
        pass

    @abstractmethod
    def get(self, pointer: str) -> bytes:
        """Retrieve blob from Cascade by pointer.

        Args:
            pointer: Content-addressed pointer (cascade://...)

        Returns:
            Encrypted blob bytes

        Raises:
            NotFoundError: If pointer not found
            ValidationError: If pointer format invalid
        """
        pass


class NotFoundError(Exception):
    """Raised when pointer not found in Cascade."""
    pass


class ValidationError(Exception):
    """Raised when pointer format is invalid."""
    pass
