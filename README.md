# tuya-beacon-linux

**Control a Bluetooth-only Tuya lamp from your Linux PC. No phone, no gateway, no cloud.**

[Leia em português](README.pt-BR.md)

Many cheap Tuya / Smart Life bulbs have no Wi-Fi. They speak *Beacon Mesh*: one-way Bluetooth advertisements. Tuya says you need a gateway. Your laptop's Bluetooth can send the same advertisements.

<img alt="lamp on, lamp color purple, lamp bright 30, lamp white 80 in a terminal, each answered with ok" src="docs/demo.gif">

```
lamp on | off
lamp bright 30          # 1-100
lamp temp 80            # white, 0 warm .. 100 cold
lamp color purple       # red orange yellow green cyan blue purple pink, or a hue 0-359
```

## The byte nobody documents

- The advertisement **must start with the Flags element `02 01 06`**.
- Without it the lamp ignores commands that are otherwise perfect, even byte-identical to the phone's.
- The most complete public write-up of the protocol leaves it out.

More in [docs/protocol.md](docs/protocol.md).

## Does it fit my lamp?

- It works in the Tuya or Smart Life app over Bluetooth only (paired without Wi-Fi).
- `capture` (first install step) hears its OFF and ON. If it hears nothing, see [docs/alternatives.md](docs/alternatives.md).
- Tested on **one** lamp, Ubuntu 24.04, GNOME 46: [docs/limits.md](docs/limits.md).

## Install

**What you need**

- The lamp paired in one of these phone apps:
    - **Tuya** (Google Play: *Tuya - Smart Life, Smart Living*, by Tuya Smart Inc.)
    - **Smart Life** (*Smart Life - Smart Living*)
    - Other brand apps built on Tuya: not tested.
- Your phone at hand, with the lamp nearby.
- A Linux PC in the same room, **Bluetooth turned on**, Python 3.8+ and systemd.

**Steps**

```bash
git clone https://github.com/oLucasAguilar/tuya-beacon-linux && cd tuya-beacon-linux
```

1. **Let the PC hear the lamp.**
    ```bash
    sudo bin/tuya-beacon capture
    ```
    While it listens, open the app on your phone and turn the lamp **off, then on**. The PC picks up both commands over Bluetooth.

2. **Get the lamp's key.**
    ```bash
    bin/tuya-beacon login
    ```
    Type your user code (app: Me > Settings > Account and Security), then scan the QR it shows with the same app. [Why a QR code?](#why-a-qr-code)

3. **Test it.**
    ```bash
    sudo bin/tuya-beacon off
    ```
    The lamp turns off. That's it, the PC can talk to it.

4. **Install.**
    ```bash
    sudo ./install.sh --gnome
    ```
    From now on, `lamp on` works without `sudo`, and the top-bar menu appears after you log out and back in. Without `--gnome`, you get only the `lamp` command.

QR login not working? Get the key on Tuya's developer website: [docs/local-key.md](docs/local-key.md).

### Why a QR code

- Commands are encrypted with your lamp's key, which never goes over the air.
- `login` reads it once from your account in the app.
- The app may ask you to confirm "Home Assistant". [Why](docs/limits.md#by-design).
- After setup, nothing talks to the cloud.

**Prefer Claude to do it?** Paste into Claude Code:

```
Install tuya-beacon-linux following https://github.com/oLucasAguilar/tuya-beacon-linux/blob/main/llms-install.md
```

It runs the steps and tells you when it is your turn (the phone, `sudo`).

## Just the code

Building your own interface? Two small files do the work:

```python
from tuyabeacon import p2
from tuyabeacon.radio import Radio

frame = p2.build_frame(src=b"\x80\x01", dst=b"\x00\x02", seq=1000,
                       payload=p2.ON, local_key=local_key, beacon_key=beacon_key)
Radio("hci0").advertise([p2.advertisement(frame)])   # needs root or CAP_NET_RAW
```

- [`tuyabeacon/p2.py`](tuyabeacon/p2.py): frames, DP payloads, beaconKey recovery
- [`tuyabeacon/radio.py`](tuyabeacon/radio.py): raw HCI advertising and scanning
- [`tuyabeacon/lamp.py`](tuyabeacon/lamp.py): the DP map and state behind `lamp`
- Tests: `python3 -m unittest discover tests`

## Credits

Built on other people's reverse engineering: [NOTICE.md](NOTICE.md). MIT License.
