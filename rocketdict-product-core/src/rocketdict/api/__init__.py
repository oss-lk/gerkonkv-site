"""Versioned public API surface for RocketDict Product Core."""

from .contracts import API_VERSION
from .client import RocketDictAPI

__all__ = ["API_VERSION", "RocketDictAPI"]
