from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from typing_extensions import Self

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice

from .auth import calculate_auth_response
from .constants import (
    AUTH_UUID,
    CONTROL_UUID,
    DEVICE_NAME,
    FIRMWARE_UUID,
    HARDWARE_UUID,
    MANUFACTURER_UUID,
    MODEL_UUID,
    SERIAL_UUID,
    SOFTWARE_UUID,
    TELEMETRY_UUID,
)
from .models import ControlState, DeviceInfo, Telemetry

_LOGGER = logging.getLogger(__name__)

ControlCallback = Callable[[ControlState], Any]
TelemetryCallback = Callable[[Telemetry], Any]


class HypervoltError(RuntimeError):
    """Base error for Hypervolt BLE operations."""


class HypervoltNotFoundError(HypervoltError):
    """Raised when no matching device is found."""


class HypervoltAuthenticationError(HypervoltError):
    """Raised when an authenticated BLE session cannot be initialized."""


class HypervoltCommandNotConfirmedError(HypervoltError):
    """Raised when a command write succeeds but no matching status arrives."""

    def __init__(self, requested_speed: int, observed_speed: int | None = None) -> None:
        self.requested_speed = requested_speed
        self.observed_speed = observed_speed
        if observed_speed is None:
            detail = "no control notification was received"
        else:
            detail = f"device reported speed {observed_speed}"
        super().__init__(f"Speed {requested_speed} was not confirmed: {detail}")


class Hypervolt:
    """Local BLE client for supported Hypervolt devices.

    Version 1.0 is tested on the Hypervolt 2 (HV200).
    """

    def __init__(self, device: BLEDevice, *, timeout: float = 30.0) -> None:
        self.device = device
        self.timeout = timeout
        self._client: BleakClient | None = None
        self._control_callbacks: list[ControlCallback] = []
        self._telemetry_callbacks: list[TelemetryCallback] = []
        self._control_condition = asyncio.Condition()
        self._telemetry_condition = asyncio.Condition()
        self.control_state: ControlState | None = None
        self.telemetry: Telemetry | None = None
        self.device_info: DeviceInfo | None = None

    @classmethod
    async def discover(
        cls,
        *,
        name: str = DEVICE_NAME,
        timeout: float = 15.0,
    ) -> Hypervolt:
        """Find a nearby Hypervolt by advertised name."""
        device = await BleakScanner.find_device_by_filter(
            lambda candidate, adv: name.lower()
            in (candidate.name or adv.local_name or "").lower(),
            timeout=timeout,
        )
        if device is None:
            raise HypervoltNotFoundError(f"{name} was not found")
        return cls(device)

    @property
    def is_connected(self) -> bool:
        return bool(self._client and self._client.is_connected)

    def add_control_callback(self, callback: ControlCallback) -> None:
        self._control_callbacks.append(callback)

    def add_telemetry_callback(self, callback: TelemetryCallback) -> None:
        self._telemetry_callbacks.append(callback)

    async def connect(self) -> None:
        """Connect, authenticate, subscribe, and read device information."""
        if self.is_connected:
            return
        _LOGGER.debug("Connecting to %s", self.device.address)
        self._client = BleakClient(
            self.device,
            timeout=self.timeout,
            winrt={"use_cached_services": False},
        )
        await self._client.connect()
        try:
            challenge = bytes(await self._client.read_gatt_char(AUTH_UUID))
            response = calculate_auth_response(self.device.address, challenge)
            await self._client.write_gatt_char(AUTH_UUID, response, response=True)
            await self._client.start_notify(CONTROL_UUID, self._on_control)
            await self._client.start_notify(TELEMETRY_UUID, self._on_telemetry)
            self.device_info = await self.read_device_info()
            _LOGGER.debug("Authenticated session initialized")
        except Exception as exc:
            await self._safe_disconnect()
            raise HypervoltAuthenticationError(
                f"Could not initialize authenticated session: {exc}"
            ) from exc

    async def disconnect(self) -> None:
        """Disconnect without changing motor state."""
        await self._safe_disconnect()

    async def __aenter__(self) -> Self:
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.disconnect()

    async def set_speed(
        self,
        speed: int,
        *,
        confirm: bool = True,
        timeout: float = 1.5,
    ) -> ControlState | None:
        """Set speed 0-3 and optionally wait for a matching notification."""
        if speed not in range(4):
            raise ValueError("Hypervolt speed must be 0, 1, 2, or 3")
        client = self._require_client()
        previous_timestamp = self.control_state.received_at if self.control_state else None
        await client.write_gatt_char(CONTROL_UUID, bytes((speed,)), response=True)
        if not confirm:
            return None
        try:
            return await self.wait_for_speed(
                speed,
                timeout=timeout,
                after=previous_timestamp,
            )
        except TimeoutError as exc:
            observed = self.control_state.speed if self.control_state else None
            raise HypervoltCommandNotConfirmedError(speed, observed) from exc

    async def stop(
        self,
        *,
        confirm: bool = True,
        timeout: float = 1.5,
    ) -> ControlState | None:
        """Stop the motor."""
        return await self.set_speed(0, confirm=confirm, timeout=timeout)

    async def wait_for_speed(
        self,
        speed: int,
        *,
        timeout: float = 1.5,
        after=None,
    ) -> ControlState:
        def predicate() -> bool:
            state = self.control_state
            if state is None or state.speed != speed:
                return False
            return after is None or state.received_at > after

        async with self._control_condition:
            if predicate():
                assert self.control_state is not None
                return self.control_state
            try:
                await asyncio.wait_for(
                    self._control_condition.wait_for(predicate),
                    timeout=timeout,
                )
            except asyncio.TimeoutError as exc:
                raise TimeoutError(f"Speed {speed} was not reported") from exc
        assert self.control_state is not None
        return self.control_state

    async def wait_for_control(self, timeout: float = 2.0) -> ControlState:
        """Wait for the first speed/load notification.

        The device does not send an initial control state on subscription. If it
        was already running, a notification normally appears only when speed or
        load level changes.
        """
        if self.control_state is not None:
            return self.control_state
        async with self._control_condition:
            try:
                await asyncio.wait_for(
                    self._control_condition.wait_for(lambda: self.control_state is not None),
                    timeout=timeout,
                )
            except asyncio.TimeoutError as exc:
                raise TimeoutError("No control notification received") from exc
        assert self.control_state is not None
        return self.control_state

    async def wait_for_telemetry(self, timeout: float = 3.0) -> Telemetry:
        """Wait for the first extended telemetry notification."""
        if self.telemetry is not None:
            return self.telemetry
        async with self._telemetry_condition:
            try:
                await asyncio.wait_for(
                    self._telemetry_condition.wait_for(lambda: self.telemetry is not None),
                    timeout=timeout,
                )
            except asyncio.TimeoutError as exc:
                raise TimeoutError("No telemetry notification received") from exc
        assert self.telemetry is not None
        return self.telemetry

    async def read_device_info(self) -> DeviceInfo:
        client = self._require_client()

        async def text(uuid: str) -> str | None:
            try:
                return bytes(await client.read_gatt_char(uuid)).decode(
                    "utf-8", errors="replace"
                ).rstrip("\x00\n")
            except Exception:  # noqa: BLE001 - optional device-info field
                return None

        return DeviceInfo(
            manufacturer=await text(MANUFACTURER_UUID),
            model=await text(MODEL_UUID),
            serial=await text(SERIAL_UUID),
            hardware=await text(HARDWARE_UUID),
            firmware=await text(FIRMWARE_UUID),
            software=await text(SOFTWARE_UUID),
        )

    def _require_client(self) -> BleakClient:
        if not self._client or not self._client.is_connected:
            raise HypervoltError("Hypervolt is not connected")
        return self._client

    async def _safe_disconnect(self) -> None:
        client, self._client = self._client, None
        if client and client.is_connected:
            for uuid in (CONTROL_UUID, TELEMETRY_UUID):
                try:
                    await client.stop_notify(uuid)
                except Exception as exc:  # noqa: BLE001 - best-effort cleanup
                    _LOGGER.debug("Could not stop notifications for %s: %s", uuid, exc)
            await client.disconnect()

    def _on_control(self, _sender, data: bytearray) -> None:
        try:
            state = ControlState.parse(bytes(data))
        except ValueError:
            return
        self.control_state = state
        asyncio.create_task(self._notify_control_waiters())
        for callback in tuple(self._control_callbacks):
            callback(state)

    async def _notify_control_waiters(self) -> None:
        async with self._control_condition:
            self._control_condition.notify_all()

    def _on_telemetry(self, _sender, data: bytearray) -> None:
        try:
            telemetry = Telemetry.parse(bytes(data))
        except ValueError:
            return
        self.telemetry = telemetry
        asyncio.create_task(self._notify_telemetry_waiters())
        for callback in tuple(self._telemetry_callbacks):
            callback(telemetry)

    async def _notify_telemetry_waiters(self) -> None:
        async with self._telemetry_condition:
            self._telemetry_condition.notify_all()


# Backward-friendly alias for code written during early testing.
Hypervolt2 = Hypervolt
