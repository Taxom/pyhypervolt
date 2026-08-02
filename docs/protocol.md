# Hypervolt BLE protocol

Observed on Hypervolt 2 / HV200, hardware 2.2.0 and firmware 1.15.0.

## Custom service

`31cb456a-3c31-4e56-8c2b-e8f479d2b056`

| Characteristic | Properties | Purpose |
|---|---|---|
| `...456b` | Read, Write | Undocumented service/diagnostic buffer |
| `...456c` | Write, Notify | Speed command and fast status |
| `...456d` | Notify | Extended telemetry |
| `...456e` | Read | Static undocumented data |
| `...4570` | Read, Write | Challenge-response authentication |

## Authentication

1. Read `4570` once. It returns four bytes: `01 XX XX XX`.
2. Calculate the response from the challenge and Bluetooth address.
3. Write the four-byte response to `4570` with response enabled.
4. Subscribe to `456c` and `456d`.

The challenge changes on every read. Standard BLE bonding is not required.
The implementation is in `src/pyhypervolt/auth.py`.

## Speed and load status (`456c`)

Write one byte:

| Value | Meaning |
|---:|---|
| `00` | Stop |
| `01` | Speed 1 |
| `02` | Speed 2 |
| `03` | Speed 3 |

Values `04` and `05` were ignored by the tested Hypervolt 2.

Notifications contain two bytes:

- byte 0: actual speed, `0..3`
- byte 1: quantized load/pressure indication, `0..3`

The device does not send an initial `456c` state immediately after subscription.
If it was already running, the first notification normally arrives when speed or
load level changes.

## Extended telemetry (`456d`)

Notifications contain 14 bytes:

| Offset | Size | Interpretation |
|---:|---:|---|
| 0 | 8 | observed as zero in tested conditions |
| 8 | 2 | raw motor-load/current proxy, big-endian |
| 10 | 2 | battery voltage in 0.01 V, big-endian |
| 12 | 1 | temperature in degrees Celsius |
| 13 | 1 | flags, meaning unknown |

Example:

`00 00 00 00 00 00 00 00 0E 48 05 E5 1B 00`

- raw motor load: `0x0E48`
- battery voltage: `0x05E5 / 100 = 15.09 V`
- temperature: `0x1B = 27 °C`

## Charging behavior

The device accepts the BLE write while charging, but the motor remains inhibited
and no matching speed confirmation is received.
