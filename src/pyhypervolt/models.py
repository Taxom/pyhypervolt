from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True, slots=True)
class ControlState:
    speed: int
    load_level: int
    received_at: datetime

    @classmethod
    def parse(cls, payload: bytes) -> "ControlState":
        if len(payload) != 2:
            raise ValueError(f"Expected 2-byte control status, got {len(payload)}")
        return cls(payload[0], payload[1], datetime.now(timezone.utc))


@dataclass(frozen=True, slots=True)
class Telemetry:
    raw_payload: bytes
    motor_load_raw: int
    battery_voltage: float
    temperature_c: int
    flags: int
    received_at: datetime

    @classmethod
    def parse(cls, payload: bytes) -> "Telemetry":
        if len(payload) != 14:
            raise ValueError(f"Expected 14-byte telemetry packet, got {len(payload)}")
        return cls(
            raw_payload=bytes(payload),
            motor_load_raw=int.from_bytes(payload[8:10], "big"),
            battery_voltage=int.from_bytes(payload[10:12], "big") / 100.0,
            temperature_c=payload[12],
            flags=payload[13],
            received_at=datetime.now(timezone.utc),
        )


@dataclass(frozen=True, slots=True)
class DeviceInfo:
    manufacturer: str | None = None
    model: str | None = None
    serial: str | None = None
    hardware: str | None = None
    firmware: str | None = None
    software: str | None = None
