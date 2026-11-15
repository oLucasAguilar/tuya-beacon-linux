"""Tuya Beacon Mesh "P2" frames: build, parse, DP payloads and beaconKey recovery.

A P2 command is a 26-byte frame carried in a BLE advertisement:

    byte 0       header: (frame_type << 3) | 3
    bytes 1-2    source address (we use 0x8001, separate from the phone app)
    bytes 3-4    destination node (the lamp, e.g. 0x0002)
    bytes 5-6    sequence number, big-endian, must keep increasing
    byte 7       sub-command (0x05 = set DPs)
    byte 8       CRC-8 of the 16-byte plaintext
    bytes 9-24   XXTEA(plaintext, localKey) XOR beaconKey
    byte 25      CRC-8 of (header & 0xFC) + bytes 1-24 before the XOR

The advertisement MUST start with the Flags element 02 01 06. Without it the
lamp silently ignores the command. See docs/protocol.md.
"""
from .crypto import xxtea, crc8

FLAGS = b"\x02\x01\x06"
FRAME_LEN = 26
DP_RAW, DP_BOOL, DP_VALUE, DP_STRING, DP_ENUM = 0, 1, 2, 3, 4
SET_DPS = 0x05


def key_from_string(key: str) -> bytes:
    """Tuya keys: 16 characters are used as ASCII, 32 hex characters are decoded."""
    if len(key) == 16:
        return key.encode()
    if len(key) == 32:
        return bytes.fromhex(key)
    raise ValueError("key must be 16 characters or 32 hex digits")


def dp_payload(dps) -> bytes:
    """dps: iterable of (dp_id, dp_type, value_bytes). Returns the TLV payload."""
    out = b"".join(bytes([dp_id, (dp_type << 4) | len(value)]) + value
                   for dp_id, dp_type, value in dps)
    if len(out) > 16:
        raise ValueError("DP payload is longer than 16 bytes")
    return out


def dp_parse(payload: bytes):
    dps, i = [], 0
    while i + 2 <= len(payload) and payload[i]:
        dp_id, kind = payload[i], payload[i + 1]
        size = kind & 0x0F
        dps.append((dp_id, kind >> 4, payload[i + 2:i + 2 + size]))
        i += 2 + size
    return dps


def build_frame(src: bytes, dst: bytes, seq: int, payload: bytes,
                local_key: bytes, beacon_key: bytes,
                frame_type: int = 1, sub_cmd: int = SET_DPS) -> bytes:
    plain = payload.ljust(16, b"\0")
    middle = src + dst + seq.to_bytes(2, "big") + bytes([sub_cmd, crc8(plain)])
    cipher = xxtea(plain, local_key)
    header = (frame_type << 3 | 3) & 0xFF
    check = crc8(bytes([header & 0xFC]) + middle + cipher)
    masked = bytes(c ^ m for c, m in zip(cipher, beacon_key))
    return bytes([header]) + middle + masked + bytes([check])


def parse_frame(frame: bytes, local_key: bytes, beacon_key: bytes):
    """Returns a dict, or None when the frame does not check out with these keys."""
    if len(frame) != FRAME_LEN:
        return None
    cipher = bytes(c ^ m for c, m in zip(frame[9:25], beacon_key))
    if crc8(bytes([frame[0] & 0xFC]) + frame[1:9] + cipher) != frame[25]:
        return None
    plain = xxtea(cipher, local_key, decrypt=True)
    if crc8(plain) != frame[8]:
        return None
    return {"src": frame[1:3], "dst": frame[3:5],
            "seq": int.from_bytes(frame[5:7], "big"),
            "sub_cmd": frame[7], "payload": plain}


def advertisement(frame: bytes) -> bytes:
    """31-byte advertising data: Flags, then the frame as a 16-bit UUID list."""
    return FLAGS + bytes([len(frame) + 1, 0x03]) + frame


ON = dp_payload([(1, DP_BOOL, b"\x01")])
OFF = dp_payload([(1, DP_BOOL, b"\x00")])


def recover_beacon_key(frame: bytes, payload: bytes, local_key: bytes) -> bytes:
    """beaconKey = XXTEA(known plaintext, localKey) XOR the masked bytes of a real frame."""
    cipher = xxtea(payload.ljust(16, b"\0"), local_key)
    return bytes(a ^ b for a, b in zip(cipher, frame[9:25]))


def find_frame(adv_data: bytes):
    """The 26-byte P2 frame inside advertising data, or None."""
    i = 0
    while i < len(adv_data):
        size = adv_data[i]
        if size == 0 or i + 1 + size > len(adv_data):
            return None
        if adv_data[i + 1] == 0x03 and size - 1 == FRAME_LEN:
            return adv_data[i + 2:i + 1 + size]
        i += size + 1
    return None
