import asyncio

from pyhypervolt import Hypervolt


async def main() -> None:
    hv = await Hypervolt.discover()

    hv.add_control_callback(lambda state: print("control", state))
    hv.add_telemetry_callback(lambda data: print("telemetry", data))

    async with hv:
        await asyncio.sleep(30)


asyncio.run(main())
