import tempfile
import threading
import unittest
from pathlib import Path

from tower.clock import FakeClock
from tower.config import SerialSection
from tower.rt.serial_source import (SerialSource, SourceUnavailable, build_charmap, check_latency_timer,
                                    decode)

DEFAULT = SerialSection().charmap


class DecodeTest(unittest.TestCase):
    def test_every_bell_both_cases_decodes_uniquely(self):
        """The 11/12 regression: E and T must decode in either case."""
        table = build_charmap(DEFAULT)
        for bell, ch in enumerate(DEFAULT, start=1):
            for variant in (ch.upper(), ch.lower()):
                with self.subTest(bell=bell, char=variant):
                    self.assertEqual(decode(variant.encode(), table), ([bell], 0))

    def test_bells_11_and_12(self):
        table = build_charmap(DEFAULT)
        self.assertEqual(decode(b"EeTt", table), ([11, 11, 12, 12], 0))

    def test_noise_counted_line_endings_ignored(self):
        table = build_charmap(DEFAULT)
        self.assertEqual(decode(b"1\r\n2\xff?", table), ([1, 2], 2))

    def test_charmap_validation(self):
        for bad in ("123", "1234567890ETABCe", "1234567890ETABCD!"):
            with self.subTest(chars=bad), self.assertRaises(ValueError):
                build_charmap(bad)

    def test_golden_stream_rounds_on_twelve(self):
        """Rounds on 12, as the box would send it. Replace with a capture from the real box."""
        table = build_charmap(DEFAULT)
        stream = b"1234567890ET" * 2
        self.assertEqual(decode(stream, table)[0], list(range(1, 13)) * 2)


class FakeSerial:
    def __init__(self, chunks, then_fail=False):
        self.chunks = list(chunks)
        self.then_fail = then_fail
        self.closed = False

    def read(self, n):
        if self.chunks:
            return self.chunks.pop(0)
        if self.then_fail:
            raise OSError("device disconnected")
        return b""

    def close(self):
        self.closed = True


class SerialSourceTest(unittest.TestCase):
    def make(self, devices, port="/dev/ttyFAKE"):
        clock = FakeClock(50.0)
        devs = iter(devices)

        def opener(p, baud):
            try:
                return next(devs)
            except StopIteration:
                raise OSError("no such device") from None

        src = SerialSource(usb_ids=[], charmap=DEFAULT, clock=clock, port=port, opener=opener, retry_s=0)
        return src, clock

    def take(self, src, n):
        out = []
        for p in src:
            out.append(p)
            if len(out) == n:
                src.stop.set()
                break
        return out

    def test_pulses_and_backdating_within_a_read(self):
        src, clock = self.make([FakeSerial([b"12", b"3"])])
        pulses = self.take(src, 3)
        self.assertEqual([p.bell for p in pulses], [1, 2, 3])
        char = 10 / 2400
        self.assertAlmostEqual(pulses[1].t_rx - pulses[0].t_rx, char)
        self.assertEqual([p.seq for p in pulses], [1, 2, 3])
        self.assertEqual(src.stats.status, "open")

    def test_reconnects_after_unplug(self):
        first = FakeSerial([b"1"], then_fail=True)
        src, _ = self.make([first, FakeSerial([b"2"])])
        pulses = self.take(src, 2)
        self.assertEqual([p.bell for p in pulses], [1, 2])
        self.assertEqual(src.stats.reopens, 1)
        self.assertTrue(first.closed)

    def test_absent_device_reported(self):
        src, _ = self.make([])
        threading.Timer(0.2, src.stop.set).start()
        self.assertEqual(list(src), [])
        self.assertEqual(src.stats.status, "absent")

    def test_no_matching_usb_device(self):
        src = SerialSource(usb_ids=["dead:beef"], charmap=DEFAULT, clock=FakeClock())
        with self.assertRaises(SourceUnavailable):
            src._open()


class LatencyTimerTest(unittest.TestCase):
    def test_reads_and_warns(self):
        sysfs = Path(tempfile.mkdtemp())
        (sysfs / "ttyUSB0").mkdir()
        (sysfs / "ttyUSB0" / "latency_timer").write_text("16\n")
        with self.assertLogs("tower.rt.serial_source", "ERROR"):
            self.assertEqual(check_latency_timer("/dev/ttyUSB0", sysfs), 16)
        (sysfs / "ttyUSB0" / "latency_timer").write_text("1\n")
        self.assertEqual(check_latency_timer("/dev/ttyUSB0", sysfs), 1)
        self.assertIsNone(check_latency_timer("/dev/ttyACM0", sysfs))
