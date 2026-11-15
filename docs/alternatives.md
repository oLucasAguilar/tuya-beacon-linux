# Alternatives

Searched on 15 November 2026 (web search and GitHub), reading each project's README. Know one that is missing? Open an issue.

| Project | What it is | Works with Beacon P2 lamps | When it is the better choice |
|---|---|---|---|
| [SunsetLampHATuyaBridge](https://github.com/FinnGrndl/SunsetLampHATuyaBridge) | Home Assistant app + integration, through HA's Bluetooth adapter | yes (power, colour, brightness; its README says no colour temperature) | you run Home Assistant and want automations |
| [universal_proxy](https://github.com/bbangert/universal_proxy) | Nerves firmware that turns a Raspberry Pi into a proxy for Home Assistant; has a Tuya Beacon Mesh module | yes, per its code and notes | you want a dedicated box next to Home Assistant |
| [beacon-cooked](https://github.com/MadeinTaly/beacon-cooked) | gateway + Home Assistant integration (MQTT) for Tuya Beacon lights | no: it speaks the AK80x Beacon flavour, which our P2 lamp ignored | your lamp is AK80x Beacon |
| [ha_tuya_ble](https://github.com/airy10/ha_tuya_ble) | Home Assistant integration for Tuya BLE (connected) devices | no: its README says mesh lights are not compatible | the device connects over BLE (Fingerbot, sensors) |
| [python-tuya-ble](https://github.com/redphx/python-tuya-ble) | Python library for Tuya BLE, marked work in progress | no, other protocol | - |
| [tinytuya](https://github.com/jasonacox/tinytuya), LocalTuya | local Wi-Fi control | no | the lamp has Wi-Fi |
| A Tuya Bluetooth gateway | hardware hub + Tuya cloud | yes | you are fine with the cloud |

We found no desktop app or GNOME extension for these lamps, and no Python library for Beacon Mesh P2. Two searches finding nothing is not proof that none exists.

## Why this one

- Runs on the PC you already have: no Home Assistant, no extra hardware.
- Controlling the lamp needs only the Python standard library. The one-time QR login installs Tuya's official SDK in its own folder.
- A small `p2.py` you can read in five minutes, if you want to build your own interface.
