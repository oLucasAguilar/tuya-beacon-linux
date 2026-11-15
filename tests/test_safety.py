"""Behaviour the security review asked for. Run with: python3 -m unittest discover tests"""
import importlib.machinery
import importlib.util
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tuyabeacon import lamp  # noqa: E402
from tuyabeacon.radio import Radio  # noqa: E402


def load_script(name):
    loader = importlib.machinery.SourceFileLoader(name, str(ROOT / "bin" / name))
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader(name, loader))
    loader.exec_module(module)
    return module


class ConfigHome(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        os.environ["TUYA_BEACON_HOME"] = self.folder.name

    def tearDown(self):
        del os.environ["TUYA_BEACON_HOME"]
        self.folder.cleanup()


class WriteJsonTest(ConfigHome):
    def test_symlink_is_replaced_not_followed(self):
        target = Path(self.folder.name) / "elsewhere.txt"
        target.write_text("untouched")
        link = Path(self.folder.name) / "seq.json"
        link.symlink_to(target)
        lamp.write_json("seq.json", {"seq": 1})
        self.assertEqual(target.read_text(), "untouched")
        self.assertFalse(link.is_symlink())

    def test_private_file_is_never_readable_by_others(self):
        lamp.write_json("keys.json", {"a": 1}, private=True)
        mode = stat.S_IMODE((Path(self.folder.name) / "keys.json").stat().st_mode)
        self.assertEqual(mode, 0o600)

    def test_file_that_is_not_an_object_reads_as_missing(self):
        (Path(self.folder.name) / "state.json").write_text("[]")
        self.assertEqual(lamp.read_json("state.json", {"x": 1}), {"x": 1})


class SequenceTest(ConfigHome):
    def test_used_up_counter_is_a_clear_error(self):
        lamp.write_json("seq.json", {"seq": 0xFFFF})
        with self.assertRaises(RuntimeError):
            lamp.next_seq(1)


class DaemonInputTest(ConfigHome):
    def test_no_command_takes_the_daemon_down(self):
        lampd = load_script("lampd")
        original = lamp.run

        def boom(*_args, **_kwargs):
            raise TypeError("unexpected")

        try:
            lamp.run = boom
            for line in ["bright", "temp", "", "x" * 300, "color \x1b[31m"]:
                self.assertIsInstance(lampd.handle(line), str)
        finally:
            lamp.run = original

    def test_number_commands_without_number(self):
        for cmd in ("bright", "temp"):
            with self.assertRaises(ValueError):
                lamp.payloads(cmd, None, {})


class RadioTest(unittest.TestCase):
    def test_adapter_from_environment(self):
        os.environ["TUYA_BEACON_ADAPTER"] = "hci1"
        try:
            self.assertEqual(Radio().adapter, "hci1")
        finally:
            del os.environ["TUYA_BEACON_ADAPTER"]

    def test_adapter_name_is_validated(self):
        with self.assertRaises(ValueError):
            Radio("hci0; rm")


if __name__ == "__main__":
    unittest.main()
