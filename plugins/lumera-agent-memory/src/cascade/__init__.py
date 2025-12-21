"""Cascade storage layer (mock + future live connector)."""

from .interface import CascadeConnector, NotFoundError, ValidationError
from .mock_fs import MockCascadeConnector

__all__ = [
    "CascadeConnector",
    "NotFoundError",
    "ValidationError",
    "MockCascadeConnector",
]
