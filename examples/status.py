import asyncio

from pyhypervolt import Hypervolt


async def main() -> None:
    hv = await Hypervolt.discover()
    async with hv:
        telemetry = await hv.wait_for_telemetry()
        print(telemetry)


asyncio.run(main())
