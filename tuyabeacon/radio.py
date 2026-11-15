"""Raw HCI access to the Bluetooth adapter: advertise one frame, or scan.

Needs CAP_NET_RAW (root, or the lampd service).
The Radio class is adapted from https://github.com/MadeinTaly/beacon-cooked
(MIT License, Copyright (c) 2026 MadeinTaly). See NOTICE.md.
"""
import os
import re
import secrets
import socket
import struct
import time


class Radio:
    def __init__(self, adapter=None):
        adapter = adapter or os.environ.get("TUYA_BEACON_ADAPTER", "hci0")
        if not re.fullmatch(r"hci\d+", adapter):
            raise ValueError("invalid adapter name: " + adapter)
        self.adapter = adapter
        self.index = int(adapter[3:])
        self.extended = None

    def command(self, ocf, payload=b"", allow_disabled=False):
        opcode = 0x2000 | ocf
        with socket.socket(socket.AF_BLUETOOTH, socket.SOCK_RAW, socket.BTPROTO_HCI) as channel:
            channel.bind((self.index,))
            channel.setsockopt(0, 2, struct.pack("<IIIH2x", 0x10, (1 << 14) | (1 << 15), 0, opcode))
            channel.settimeout(5)
            channel.send(b"\x01" + opcode.to_bytes(2, "little") + bytes([len(payload)]) + payload)
            deadline = time.monotonic() + 5
            while True:
                channel.settimeout(max(0.01, deadline - time.monotonic()))
                packet = channel.recv(512)
                if len(packet) >= 7 and packet[:2] == b"\x04\x0e" and packet[4:6] == opcode.to_bytes(2, "little"):
                    status, reply = packet[6], packet[7:]
                    break
                if (len(packet) >= 7 and packet[:2] == b"\x04\x0f"
                        and packet[5:7] == opcode.to_bytes(2, "little") and packet[3]):
                    status, reply = packet[3], b""
                    break
                if time.monotonic() >= deadline:
                    raise TimeoutError("Bluetooth command timed out")
        if status and not (allow_disabled and status == 0x0C):
            raise RuntimeError(f"Bluetooth command {ocf:#x}: status {status:#x}")
        return reply

    def detect_mode(self):
        if self.extended is None:
            self.command(0x03)
            try:
                supported = self.command(0x3B)
                self.extended = bool(supported and supported[0])
            except RuntimeError:
                self.extended = False

    def stop_advertising(self):
        self.detect_mode()
        if self.extended:
            self.command(0x39, b"\0\0", allow_disabled=True)
        else:
            self.command(0x0A, b"\0", allow_disabled=True)

    def advertise(self, ads, hold=0.5):
        """Broadcast each 31-byte advertising payload for `hold` seconds, from a random address."""
        self.detect_mode()
        self.stop_advertising()
        sender = bytes([0xC2]) + secrets.token_bytes(5)
        if self.extended:
            self.command(0x36, bytes.fromhex("011300200000200000070100000000000000007f0100010000"))
            self.command(0x35, b"\x01" + sender[::-1])
        else:
            self.command(0x05, sender[::-1])
            self.command(0x06, bytes.fromhex("200020000001000000000000000700"))
            self.command(0x09, b"\0" * 32)
        try:
            for ad in ads:
                if self.extended:
                    self.command(0x37, bytes([1, 3, 1, len(ad)]) + ad)
                    self.command(0x39, bytes.fromhex("010101000000"))
                else:
                    self.command(0x08, bytes([len(ad)]) + ad.ljust(31, b"\0"))
                    self.command(0x0A, b"\x01")
                time.sleep(hold)
        finally:
            self.stop_advertising()

    def scan(self, seconds):
        """Yield the advertising data of every report heard for `seconds`."""
        self.detect_mode()
        sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_RAW, socket.BTPROTO_HCI)
        sock.bind((self.index,))
        sock.setsockopt(0, 2, struct.pack("<IIIH2x", 0x10, 0, 1 << 30, 0))
        self.stop_advertising()
        if self.extended:
            self.command(0x42, bytes(6), allow_disabled=True)
            self.command(0x41, bytes.fromhex("0000010110001000"))
            self.command(0x42, bytes.fromhex("010000000000"))
        else:
            self.command(0x0C, b"\0\0", allow_disabled=True)
            self.command(0x0B, bytes.fromhex("01100010000000"))
            self.command(0x0C, b"\x01\0")
        deadline = time.monotonic() + seconds
        try:
            while time.monotonic() < deadline:
                sock.settimeout(max(0.05, deadline - time.monotonic()))
                try:
                    pkt = sock.recv(4096)
                except (TimeoutError, socket.timeout):
                    break
                if len(pkt) < 6 or pkt[:2] != b"\x04\x3e":
                    continue
                if pkt[3] == 0x02 and len(pkt) > 13:      # legacy advertising report
                    size = pkt[13]
                    yield pkt[14:14 + size]
                elif pkt[3] == 0x0D and len(pkt) > 28:    # extended advertising report
                    size = pkt[28]
                    yield pkt[29:29 + size]
        finally:
            if self.extended:
                self.command(0x42, bytes(6), allow_disabled=True)
            else:
                self.command(0x0C, b"\0\0", allow_disabled=True)
            sock.close()
