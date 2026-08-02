# Reverse-engineering notes

- BLE services and notifications were inspected on a personally owned device.
- Challenge-response authentication was independently reimplemented.
- Commands `00` through `03` were verified as stop and speeds 1-3.
- Values `04` and `05` were tested and ignored on Hypervolt 2.
- Fast load levels and extended motor/battery telemetry were correlated with
  physical operation.
- Motor operation was confirmed to be inhibited while charging.

No firmware, APK, account data, or proprietary application assets are included.
