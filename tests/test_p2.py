"""Run with: python3 -m unittest discover tests

Expected frames were produced by the implementation that drives the real lamp,
with made-up keys (no real lamp key is in this repo).
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tuyabeacon import lamp, p2  # noqa: E402

LOCAL_KEY = b"0123456789abcdef"
BEACON_KEY = bytes(range(16))
SRC, DST = bytes.fromhex("8001"), bytes.fromhex("0002")


def frame(payload, seq=1000):
    return p2.build_frame(SRC, DST, seq, payload, LOCAL_KEY, BEACON_KEY)


class FrameTest(unittest.TestCase):
    def test_on_matches_known_frame(self):
        self.assertEqual(frame(p2.ON).hex(), "0b8001000203e80533eb14c7a272416d6b2aa86361a7449d20b8")

    def test_purple_matches_known_frame(self):
        state = {"bright": 100}
        [payload] = lamp.payloads("color", "purple", state)
        self.assertEqual(frame(payload).hex(), "0b8001000203e8058803041de1e176d721bc1f78dcc87c5b3e62")

    def test_parse_round_trip(self):
        decoded = p2.parse_frame(frame(p2.OFF, seq=4242), LOCAL_KEY, BEACON_KEY)
        self.assertEqual(decoded["seq"], 4242)
        self.assertEqual(p2.dp_parse(decoded["payload"]), [(1, p2.DP_BOOL, b"\x00")])

    def test_wrong_key_is_rejected(self):
        self.assertIsNone(p2.parse_frame(frame(p2.ON), b"x" * 16, BEACON_KEY))

    def test_advertisement_starts_with_flags(self):
        ad = p2.advertisement(frame(p2.ON))
        self.assertEqual(len(ad), 31)
        self.assertEqual(ad[:5], bytes.fromhex("0201061b03"))
        self.assertEqual(p2.find_frame(ad), frame(p2.ON))

    def test_beacon_key_recovered_from_one_frame(self):
        self.assertEqual(p2.recover_beacon_key(frame(p2.ON), p2.ON, LOCAL_KEY), BEACON_KEY)


class LampCommandTest(unittest.TestCase):
    def test_brightness_keeps_colour_mode(self):
        state = {"mode": "color", "hue": 120}
        [payload] = lamp.payloads("bright", "40", state)
        self.assertEqual(p2.dp_parse(payload)[1], (11, p2.DP_RAW, bytes([0, 120, 100, 40])))

    def test_white_brightness_uses_app_range(self):
        [payload] = lamp.payloads("bright", "1", {"mode": "white"})
        self.assertEqual(p2.dp_parse(payload)[1][2], (10).to_bytes(4, "big"))

    def test_unknown_command(self):
        with self.assertRaises(ValueError):
            lamp.payloads("dance", None, {})

    def test_sequence_keeps_increasing(self):
        with tempfile.TemporaryDirectory() as folder:
            os.environ["TUYA_BEACON_HOME"] = folder
            try:
                first = lamp.next_seq(2)
                self.assertEqual(lamp.next_seq(1), first + 2)
            finally:
                del os.environ["TUYA_BEACON_HOME"]


if __name__ == "__main__":
    unittest.main()
