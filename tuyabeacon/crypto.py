"""XXTEA (big-endian, one 16-byte block) and CRC-8 used by Tuya Beacon frames.

Adapted from https://github.com/MadeinTaly/beacon-cooked (MIT License,
Copyright (c) 2026 MadeinTaly). See NOTICE.md.
"""
import struct

MASK = 0xFFFFFFFF
DELTA = 0x9E3779B9


def xxtea(block: bytes, key: bytes, decrypt: bool = False) -> bytes:
    if len(block) != 16 or len(key) != 16:
        raise ValueError("block and key must each be 16 bytes")
    v = list(struct.unpack(">4I", block))
    k = struct.unpack(">4I", key)

    def mix(z, y, total, p, e):
        return (((z >> 5 ^ y << 2) + (y >> 3 ^ z << 4)) ^
                ((total ^ y) + (k[(p & 3) ^ e] ^ z))) & MASK

    if decrypt:
        total = 19 * DELTA & MASK
        y = v[0]
        for _ in range(19):
            e = total >> 2 & 3
            for p in range(3, 0, -1):
                z = v[p - 1]
                v[p] = (v[p] - mix(z, y, total, p, e)) & MASK
                y = v[p]
            z = v[-1]
            v[0] = (v[0] - mix(z, y, total, 0, e)) & MASK
            y = v[0]
            total = (total - DELTA) & MASK
    else:
        total = 0
        z = v[-1]
        for _ in range(19):
            total = (total + DELTA) & MASK
            e = total >> 2 & 3
            for p in range(3):
                y = v[p + 1]
                v[p] = (v[p] + mix(z, y, total, p, e)) & MASK
                z = v[p]
            y = v[0]
            v[-1] = (v[-1] + mix(z, y, total, 3, e)) & MASK
            z = v[-1]
    return struct.pack(">4I", *v)


def crc8(data: bytes) -> int:
    """CRC-8, polynomial 0x07, initial value 0."""
    value = 0
    for byte in data:
        value ^= byte << 8
        for _ in range(8):
            value = ((value ^ 0x8380) << 1 if value & 0x8000 else value << 1) & MASK
    return value >> 8 & 255
