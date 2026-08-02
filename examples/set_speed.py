import asyncio

from pyhypervolt import Hypervolt


async def main() -> None:
    hv = await Hypervolt.discover()
    async with hv:
        await hv.set_speed(1)
        await asyncio.sleep(3)
        await hv.stop()


asyncio.run(main())
