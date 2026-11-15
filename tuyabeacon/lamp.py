"""Lamp commands on top of P2 frames: DP map, remembered state, sequence numbers.

The DP map below is the one tested on a Tuya "dj" light (product heflj0rj).
Other models may use other DP numbers: run `tuya-beacon sniff` while using the
phone app to see what it sends, and change DP_* here.

One lamp is supported today, named "lamp". Everything that belongs to a lamp
(keys, capture, state) lives in lamps/<name>/ and every function takes the name,
so a second lamp needs only the interface (CLI, lampd, menu) to pass another one.
The sequence counter is shared: the lamp only checks that it grows per source.
"""
import contextlib
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
DEFAULT_LAMP = "lamp"


def lamp_file(kind, name=DEFAULT_LAMP):
    """Config path of one lamp's file: keys, capture, localkey or state."""
    return f"lamps/{name}/{kind}.json"


def config_dir() -> Path:
    if os.environ.get("TUYA_BEACON_HOME"):
        return Path(os.environ["TUYA_BEACON_HOME"])
    home = Path.home()
    if os.geteuid() == 0 and os.environ.get("SUDO_USER"):
        home = Path(pwd.getpwnam(os.environ["SUDO_USER"]).pw_dir)
    return home / ".config" / "tuya-beacon-linux"


@contextlib.contextmanager
def as_real_user():
    """Under sudo, touch the user's config as the user, never as root.

    The config lives in the user's home, so anything there may be a symlink the
    user (or malware running as the user) planted. As the user, a symlink can only
    reach what the user could already write.
    """
    if os.geteuid() != 0 or not os.environ.get("SUDO_UID"):
        yield
        return
    uid, gid = int(os.environ["SUDO_UID"]), int(os.environ["SUDO_GID"])
    groups = os.getgroups()
    os.setgroups(os.getgrouplist(os.environ["SUDO_USER"], gid))
    os.setegid(gid)
    os.seteuid(uid)
    try:
        yield
    finally:
        os.seteuid(0)
        os.setegid(0)
        os.setgroups(groups)


def read_json(name, default=None):
    path = config_dir() / name   # resolved as root: as the user, HOME would be /root's
    try:
        with as_real_user():
            data = json.loads(path.read_text())
        return data if isinstance(data, dict) else default
    except (OSError, ValueError):
        return default


def write_json(name, data, private=False):
    """Write a config file atomically, with its final mode from the start."""
    path = config_dir() / name
    temporary = path.with_name(path.name + ".tmp")
    with as_real_user():
        path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW,
                     0o600 if private else 0o644)
        with os.fdopen(fd, "w") as file:
            if private:
                os.fchmod(file.fileno(), 0o600)
            file.write(json.dumps(data, indent=1))
        os.replace(temporary, path)   # replaces a symlink itself, never its target


def load_keys(name=DEFAULT_LAMP):
    keys = read_json(lamp_file("keys", name))
    if not keys:
        raise SystemExit("no keys yet: run `tuya-beacon capture` and `tuya-beacon derive` first")
    return (p2.key_from_string(keys["localkey"]), bytes.fromhex(keys["beaconkey"]),
            bytes.fromhex(keys["dst"]))


SEQ_MAX = 0xFFFF   # the frame carries the sequence in 2 bytes


def next_seq(count):
    seq = read_json("seq.json", {}).get("seq", 1000)
    if seq + count > SEQ_MAX:
        raise RuntimeError("sequence counter used up (65535 commands): see docs/limits.md")
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
    if cmd in ("bright", "temp") and arg is None:
        raise ValueError(f"{cmd} needs a number")
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


def run(cmd, arg=None, radio=None, name=DEFAULT_LAMP):
    local_key, beacon_key, dst = load_keys(name)
    state = read_json(lamp_file("state", name), {"on": True, "mode": "white", "bright": 100, "hue": 0, "temp": 50})
    batch = payloads(cmd, arg, state)
    seq = next_seq(len(batch))
    ads = [p2.advertisement(p2.build_frame(SRC, dst, seq + i, p, local_key, beacon_key))
           for i, p in enumerate(batch)]
    (radio or Radio()).advertise(ads)
    write_json(lamp_file("state", name), state)
    return state
