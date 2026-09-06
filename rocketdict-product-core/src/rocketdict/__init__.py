"""RocketDict maintained Product Core.

This package is a new forward-built implementation.  It is not reconstructed
historical 0.30.x source.  Public contracts are versioned independently and are
consumed by ``rocketdict-workbench``.
"""

from __future__ import annotations

__version__ = "1.0.0.dev1"


def __getattr__(name: str):
    if name == "API_VERSION":
        from .api.contracts import API_VERSION

        return API_VERSION
    if name == "RocketDictAPI":
        from .api.client import RocketDictAPI

        return RocketDictAPI
    raise AttributeError(name)


__all__ = ["__version__", "API_VERSION", "RocketDictAPI"]
