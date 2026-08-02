from __future__ import annotations

import argparse
import asyncio
import json
import logging
from datetime import datetime

from bleak import BleakScanner

from .client import Hypervolt, HypervoltCommandNotConfirmedError


def _device_info_dict(info):
    return {
        "manufacturer": info.manufacturer,
        "model": info.model,
        "serial": info.serial,
        "hardware": info.hardware,
        "firmware": info.firmware,
        "software": info.software,
    }


def _status_dict(hv: Hypervolt):
    telemetry = hv.telemetry
    control = hv.control_state
    return {
        "address": hv.device.address,
        "device": _device_info_dict(hv.device_info),
        "speed": control.speed if control else None,
        "load_level": control.load_level if control else None,
        "motor_load_raw": telemetry.motor_load_raw if telemetry else None,
        "battery_voltage": telemetry.battery_voltage if telemetry else None,
        "temperature_c": telemetry.temperature_c if telemetry else None,
        "flags": telemetry.flags if telemetry else None,
    }


async def cmd_scan(_args) -> None:
    devices = await BleakScanner.discover(timeout=10.0, return_adv=True)
    for device, adv in devices.values():
        name = device.name or adv.local_name or ""
        if "hypervolt" in name.lower():
            print(f"{name}\t{device.address}\t{adv.rssi} dBm")


async def cmd_status(args) -> None:
    hv = await Hypervolt.discover()
    async with hv:
        await hv.wait_for_telemetry(timeout=args.timeout)
        try:
            await hv.wait_for_control(timeout=args.timeout)
        except TimeoutError:
            pass
        print(json.dumps(_status_dict(hv), indent=2))


async def cmd_speed(args) -> None:
    hv = await Hypervolt.discover()
    await hv.connect()
    confirmed = False
    try:
        try:
            await hv.set_speed(args.level, timeout=args.confirm_timeout)
            confirmed = True
        except HypervoltCommandNotConfirmedError as exc:
            print(f"Command sent, but speed {args.level} was not confirmed.")
            if exc.observed_speed is not None:
                print(f"Device currently reports speed {exc.observed_speed}.")
            print("The motor may be inhibited while the charger is connected.")
            raise SystemExit(2) from exc

        print(f"Speed {args.level} confirmed")
        await asyncio.sleep(args.hold)
    finally:
        if confirmed and args.stop_on_exit and hv.is_connected:
            try:
                await hv.stop(timeout=args.confirm_timeout)
            except HypervoltCommandNotConfirmedError:
                print("Warning: stop command was not confirmed.")
        await hv.disconnect()


async def cmd_stop(args) -> None:
    hv = await Hypervolt.discover()
    await hv.connect()
    try:
        try:
            await hv.stop(timeout=args.confirm_timeout)
            print("Stop confirmed")
        except HypervoltCommandNotConfirmedError:
            print("Stop command sent, but no confirmation was received.")
            raise SystemExit(2)
    finally:
        await hv.disconnect()


def _print_table_status(status: dict) -> None:
    speed = "?" if status["speed"] is None else str(status["speed"])
    load = "?" if status["load_level"] is None else str(status["load_level"])
    voltage = "?" if status["battery_voltage"] is None else f'{status["battery_voltage"]:.2f}V'
    temp = "?" if status["temperature_c"] is None else f'{status["temperature_c"]}C'
    raw = "?" if status["motor_load_raw"] is None else str(status["motor_load_raw"])
    flags = "?" if status["flags"] is None else f'0x{status["flags"]:02X}'
    print(
        f"{datetime.now().strftime('%H:%M:%S')}  {speed:^5} {load:^4} "
        f"{voltage:>7}  {temp:>4} {raw:>8} {flags:>5}",
        flush=True,
    )


async def cmd_monitor(args) -> None:
    hv = await Hypervolt.discover()
    await hv.connect()
    loop = asyncio.get_running_loop()
    deadline = loop.time() + args.seconds
    next_output = loop.time()
    try:
        if not args.json:
            print("Time      Speed Load Battery  Temp Raw load Flags")
            print("--------  ----- ---- -------  ---- -------- -----")

        while loop.time() < deadline:
            now = loop.time()
            if now < next_output:
                await asyncio.sleep(min(next_output - now, deadline - now))
                continue

            status = _status_dict(hv)
            if args.json:
                status["timestamp"] = datetime.now().astimezone().isoformat(timespec="seconds")
                print(json.dumps(status, separators=(",", ":")), flush=True)
            else:
                _print_table_status(status)
            next_output += args.interval
    finally:
        # Monitoring is passive: disconnect without stopping the motor.
        await hv.disconnect()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hypervolt")
    parser.add_argument("--debug", action="store_true", help="enable debug logging")
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="scan for nearby Hypervolt devices")
    scan.set_defaults(func=cmd_scan)

    status = sub.add_parser("status", help="show device information and telemetry")
    status.add_argument(
        "--timeout",
        type=float,
        default=2.0,
        help="seconds to wait for control and telemetry notifications",
    )
    status.set_defaults(func=cmd_status)

    speed = sub.add_parser("speed", help="set speed 0-3")
    speed.add_argument("level", type=int, choices=range(0, 4))
    speed.add_argument(
        "--hold",
        type=float,
        default=5.0,
        help="seconds before stopping and disconnecting",
    )
    speed.add_argument(
        "--confirm-timeout",
        type=float,
        default=1.5,
        help="seconds to wait for speed confirmation",
    )
    speed.add_argument(
        "--leave-running",
        action="store_false",
        dest="stop_on_exit",
        help="disconnect without stopping the motor",
    )
    speed.set_defaults(func=cmd_speed, stop_on_exit=True)

    stop = sub.add_parser("stop", help="send the stop command")
    stop.add_argument("--confirm-timeout", type=float, default=1.5)
    stop.set_defaults(func=cmd_stop)

    monitor = sub.add_parser("monitor", help="print live status and telemetry")
    monitor.add_argument("--seconds", type=float, default=30.0)
    monitor.add_argument("--interval", type=float, default=1.0)
    monitor.add_argument("--json", action="store_true", help="emit newline-delimited JSON")
    monitor.set_defaults(func=cmd_monitor)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(args.func(args))
