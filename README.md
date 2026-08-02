# pyhypervolt

Unofficial local Bluetooth Low Energy client for Hyperice Hypervolt devices.
No Hyperice account, cloud connection, or BLE bonding is required.

Tested on Hypervolt 2 / HV200, hardware 2.2.0, firmware 1.15.0.

## Features

- BLE discovery and authentication
- Speeds 1-3 and stop
- Command confirmation from the device
- Battery voltage, temperature, and motor-load telemetry
- Speed and load-level notifications
- Python API and command-line interface

## Installation from source

```powershell
git clone https://github.com/Taxom/pyhypervolt.git
cd pyhypervolt
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
```

## CLI

```powershell
hypervolt scan
hypervolt status
hypervolt monitor --seconds 30
hypervolt monitor --seconds 30 --json
hypervolt speed 2 --hold 10
hypervolt stop
```

`speed` stops the motor after the hold time. Add `--leave-running` to disconnect
without stopping it.

The charger blocks motor operation. A BLE write may succeed while charging, but
the requested speed will not be confirmed.

`monitor` is passive and never stops the motor when it exits. If the device was
already running before connection, speed may initially display as unknown until
speed or load changes and the first control notification is sent.

## Python example

```python
import asyncio
from pyhypervolt import Hypervolt


async def main() -> None:
    hv = await Hypervolt.discover()
    async with hv:
        await hv.set_speed(2)
        await asyncio.sleep(5)
        await hv.stop()


asyncio.run(main())
```

## Protocol

See [`docs/protocol.md`](docs/protocol.md).

## Development

```powershell
python -m pip install -e ".[dev]"
pytest
ruff check .
```

## Legal

This project is unofficial and is not affiliated with or endorsed by Hyperice.
Hyperice and Hypervolt are trademarks of their respective owner. No firmware,
APK, or proprietary application assets are distributed.

## License

MIT. See [`LICENSE`](LICENSE).
