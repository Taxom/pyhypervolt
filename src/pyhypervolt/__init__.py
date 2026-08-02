from __future__ import annotations

from .models import ControlState, DeviceInfo, Telemetry

__all__ = [
    "Hypervolt",
    "Hypervolt2",
    "HypervoltError",
    "HypervoltNotFoundError",
    "HypervoltAuthenticationError",
    "HypervoltCommandNotConfirmedError",
    "ControlState",
    "Telemetry",
    "DeviceInfo",
]

__version__ = "1.0.0"


def __getattr__(name: str):
    if name in {
        "Hypervolt",
        "Hypervolt2",
        "HypervoltError",
        "HypervoltNotFoundError",
        "HypervoltAuthenticationError",
        "HypervoltCommandNotConfirmedError",
    }:
        from .client import (
            Hypervolt,
            Hypervolt2,
            HypervoltAuthenticationError,
            HypervoltCommandNotConfirmedError,
            HypervoltError,
            HypervoltNotFoundError,
        )

        values = {
            "Hypervolt": Hypervolt,
            "Hypervolt2": Hypervolt2,
            "HypervoltError": HypervoltError,
            "HypervoltNotFoundError": HypervoltNotFoundError,
            "HypervoltAuthenticationError": HypervoltAuthenticationError,
            "HypervoltCommandNotConfirmedError": HypervoltCommandNotConfirmedError,
        }
        return values[name]
    raise AttributeError(name)
