"""RocketDict core package with lazy public API exports."""

from __future__ import annotations

from typing import Any

__version__ = "0.30.40"
__all__ = ["API_VERSION", "RocketDictAPI", "__version__"]


def __getattr__(name: str) -> Any:
    if name == "API_VERSION":
        from rocketdict.api.contracts import API_VERSION
        return API_VERSION
    if name == "RocketDictAPI":
        from rocketdict.api.client import RocketDictAPI
        return RocketDictAPI
    raise AttributeError(name)
