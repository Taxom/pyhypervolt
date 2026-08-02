import asyncio

from bleak import BleakScanner


async def main() -> None:
    devices = await BleakScanner.discover(timeout=10.0, return_adv=True)
    for device, advertisement in devices.values():
        name = device.name or advertisement.local_name or ""
        if "hypervolt" in name.lower():
            print(name, device.address, advertisement.rssi)


asyncio.run(main())
