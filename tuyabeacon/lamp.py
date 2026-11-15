"""Lamp commands on top of P2 frames: DP map, remembered state, sequence numbers.

The DP map below is the one tested on a Tuya "dj" light (product heflj0rj).
Other models may use other DP numbers: run `tuya-beacon sniff` while using the
phone app to see what it sends, and change DP_* here.
"""
import json
import os
import pwd
from pathlib import Path

from . import p2
from .radio import Radio

DP_POWER = 1      # bool
DP_MODE = 2       # enum: 0 white, 1 colour
DP_BRIGHT = 3     # value 10..1000 (white mode)
DP_TEMP = 4       # value 0 (warm) .. 1000 (cold)
DP_COLOUR = 11    # raw: H (2 bytes, 0..359), S, V (0..100)

SRC = bytes.fromhex("8001")   # our own source address, separate from the phone app
COLOURS = {"red": 0, "orange": 30, "yellow": 60, "green": 120,
           "cyan": 180, "blue": 240, "purple": 270, "pink": 330}
USAGE = "on | off | bright 1-100 | temp 0-100 | white [1-100] | color <name|hue 0-359>"


def config_dir() -> Path:
    if os.environ.get("TUYA_BEACON_HOME"):
        return Path(os.environ["TUYA_BEACON_HOME"])
    home = Path.home()
    if os.geteuid() == 0 and os.environ.get("SUDO_USER"):
        home = Path(pwd.getpwnam(os.environ["SUDO_USER"]).pw_dir)
    return home / ".config" / "tuya-beacon-linux"


def read_json(name, default=None):
    try:
        return json.loads((config_dir() / name).read_text())
    except (OSError, ValueError):
        return default


def write_json(name, data, private=False):
    """Write a config file, owned by the real user even when run with sudo."""
    folder = config_dir()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_text(json.dumps(data, indent=1))
    if private:
        path.chmod(0o600)
    if os.geteuid() == 0 and os.environ.get("SUDO_UID"):
        uid, gid = int(os.environ["SUDO_UID"]), int(os.environ["SUDO_GID"])
        os.chown(folder, uid, gid)
        os.chown(path, uid, gid)


def load_keys():
    keys = read_json("keys.json")
    if not keys:
        raise SystemExit("no keys yet: run `tuya-beacon capture` and `tuya-beacon derive` first")
    return (p2.key_from_string(keys["localkey"]), bytes.fromhex(keys["beaconkey"]),
            bytes.fromhex(keys["dst"]))


def next_seq(count):
    seq = read_json("seq.json", {}).get("seq", 1000)
    write_json("seq.json", {"seq": seq + count})
    return seq


def _bright(pct):
    """1..100 % -> 10..1000, the app's own range."""
    return round(10 + (max(1, min(100, int(pct))) - 1) / 99 * 990)


def _colour(hue, value):
    return (DP_COLOUR, p2.DP_RAW, int(hue).to_bytes(2, "big") + bytes([100, value]))


def payloads(cmd, arg, state):
    """DP payloads for one command, updating `state` (brightness survives colour changes)."""
    if cmd in ("on", "off"):
        state["on"] = cmd == "on"
        return [p2.ON if state["on"] else p2.OFF]
    if cmd == "bright":
        state["bright"] = max(1, min(100, int(arg)))
        if state.get("mode") == "color":
            return [p2.dp_payload([(DP_MODE, p2.DP_ENUM, b"\x01"), _colour(state.get("hue", 0), state["bright"])])]
        return [p2.dp_payload([(DP_MODE, p2.DP_ENUM, b"\x00"),
                               (DP_BRIGHT, p2.DP_VALUE, _bright(state["bright"]).to_bytes(4, "big"))])]
    if cmd == "temp":
        state["mode"], state["temp"] = "white", max(0, min(100, int(arg)))
        return [p2.dp_payload([(DP_MODE, p2.DP_ENUM, b"\x00"),
                               (DP_TEMP, p2.DP_VALUE, (state["temp"] * 10).to_bytes(4, "big"))])]
    if cmd == "white":
        state["mode"] = "white"
        if arg is not None:
            state["bright"] = max(1, min(100, int(arg)))
        return [p2.dp_payload([(DP_MODE, p2.DP_ENUM, b"\x00"),
                               (DP_BRIGHT, p2.DP_VALUE, _bright(state.get("bright", 100)).to_bytes(4, "big"))])]
    if cmd == "color":
        if arg is None:
            raise ValueError("color needs a name or a hue: " + ", ".join(COLOURS))
        hue = COLOURS[arg] if arg in COLOURS else int(arg) % 360
        state["mode"], state["hue"] = "color", hue
        return [p2.dp_payload([(DP_MODE, p2.DP_ENUM, b"\x01"), _colour(hue, state.get("bright", 100))])]
    raise ValueError(f"unknown command {cmd!r}. Use: {USAGE}")


def run(cmd, arg=None, radio=None):
    local_key, beacon_key, dst = load_keys()
    state = read_json("state.json", {"on": True, "mode": "white", "bright": 100, "hue": 0, "temp": 50})
    batch = payloads(cmd, arg, state)
    seq = next_seq(len(batch))
    ads = [p2.advertisement(p2.build_frame(SRC, dst, seq + i, p, local_key, beacon_key))
           for i, p in enumerate(batch)]
    (radio or Radio(os.environ.get("TUYA_BEACON_ADAPTER", "hci0"))).advertise(ads)
    write_json("state.json", state)
    return state
