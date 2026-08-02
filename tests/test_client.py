import asyncio
import sys
import types
from datetime import datetime, timezone

import pytest

bleak = types.ModuleType("bleak")
bleak.BleakClient = object
bleak.BleakScanner = object
sys.modules.setdefault("bleak", bleak)
backends = types.ModuleType("bleak.backends")
device = types.ModuleType("bleak.backends.device")
device.BLEDevice = object
sys.modules.setdefault("bleak.backends", backends)
sys.modules.setdefault("bleak.backends.device", device)

from pyhypervolt.client import Hypervolt
from pyhypervolt.models import ControlState


@pytest.mark.asyncio
async def test_wait_for_speed_uses_notification():
    hv = object.__new__(Hypervolt)
    hv._control_condition = asyncio.Condition()
    hv.control_state = None

    async def publish():
        await asyncio.sleep(0.01)
        hv.control_state = ControlState(2, 0, datetime.now(timezone.utc))
        async with hv._control_condition:
            hv._control_condition.notify_all()

    task = asyncio.create_task(publish())
    state = await hv.wait_for_speed(2, timeout=0.5)
    await task
    assert state.speed == 2


@pytest.mark.asyncio
async def test_wait_for_speed_times_out():
    hv = object.__new__(Hypervolt)
    hv._control_condition = asyncio.Condition()
    hv.control_state = None
    with pytest.raises(TimeoutError):
        await hv.wait_for_speed(1, timeout=0.01)
