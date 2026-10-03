import io
import tempfile
import unittest
import wave
import zipfile
from pathlib import Path

import numpy as np

from tower.rt import soundpack
from tower.rt.soundpack import PackError


def wav_bytes(samples, rate=44100, width=2, channels=1):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(width)
        w.setframerate(rate)
        if width == 2:
            w.writeframes((np.asarray(samples) * 32767).astype("<i2").tobytes())
        else:
            v = (np.asarray(samples) * (2**23 - 1)).astype(np.int32)
            w.writeframes(b"".join(int(x).to_bytes(3, "little", signed=True) for x in v))
    return buf.getvalue()


MANIFEST = """schema_version = 1
id = "test-ring"
name = "Test ring"
sample_rate = 44100
[provenance]
licence = "CC0"
[[bells]]
number = 1
file = "b1.wav"
gain_db = -6.0
strike_offset_ms = { hand = 12, back = 15 }
[[bells]]
number = 2
file = "b2.wav"
"""


def make_zip(path, manifest=MANIFEST, files=None, folder=""):
    files = files if files is not None else {"b1.wav": wav_bytes([0.5] * 100), "b2.wav": wav_bytes([0.25] * 50)}
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(folder + "manifest.toml", manifest)
        for name, data in files.items():
            z.writestr(folder + name, data)
    return path


class SoundPackTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.packs = self.tmp / "packs"

    def test_install_and_load(self):
        pack = soundpack.install_zip(make_zip(self.tmp / "p.zip"), self.packs, 44100)
        self.assertEqual(pack.id, "test-ring")
        self.assertEqual(sorted(pack.bells), [1, 2])
        self.assertAlmostEqual(float(pack.bells[1].samples[0]), 0.5 * 10 ** (-6 / 20), places=3)
        self.assertEqual(pack.bells[1].offset_ms, {"hand": 12.0, "back": 15.0})
        loaded = soundpack.load("test-ring", self.packs, 44100)
        self.assertEqual(len(loaded.bells[2].samples), 50)
        self.assertEqual([p["id"] for p in soundpack.installed(self.packs)], ["synthetic", "test-ring"])

    def test_zip_with_enclosing_folder(self):
        soundpack.install_zip(make_zip(self.tmp / "p.zip", folder="My ring/"), self.packs, 44100)
        self.assertTrue((self.packs / "test-ring" / "b1.wav").is_file())

    def test_bad_wav_rejected_and_nothing_installed(self):
        z = make_zip(self.tmp / "p.zip", files={"b1.wav": b"RIFFjunk", "b2.wav": wav_bytes([0.1] * 10)})
        with self.assertRaisesRegex(PackError, "bell 1"):
            soundpack.install_zip(z, self.packs, 44100)
        self.assertEqual([p.name for p in self.packs.iterdir()], [])

    def test_missing_file(self):
        z = make_zip(self.tmp / "p.zip", files={"b1.wav": wav_bytes([0.1] * 10)})
        with self.assertRaisesRegex(PackError, "b2.wav missing"):
            soundpack.install_zip(z, self.packs, 44100)

    def test_manifest_validation(self):
        bad = {
            "path in file": MANIFEST.replace('"b1.wav"', '"../b1.wav"'),
            "reserved id": MANIFEST.replace('"test-ring"', '"synthetic"'),
            "bad id": MANIFEST.replace('"test-ring"', '"Test Ring!"'),
            "schema": MANIFEST.replace("schema_version = 1", "schema_version = 2"),
            "dup bell": MANIFEST.replace("number = 2", "number = 1"),
            "bell 17": MANIFEST.replace("number = 2", "number = 17"),
        }
        for why, text in bad.items():
            with self.subTest(why), self.assertRaises(PackError):
                soundpack.parse_manifest(text)

    def test_not_a_zip(self):
        junk = self.tmp / "x.zip"
        junk.write_bytes(b"nope")
        with self.assertRaisesRegex(PackError, "zip"):
            soundpack.install_zip(junk, self.packs, 44100)

    def test_24_bit_stereo_and_resampling(self):
        x = soundpack.read_wav(wav_bytes([0.5] * 480, rate=48000, width=3), 44100)
        self.assertEqual(len(x), 441)
        self.assertAlmostEqual(float(x[10]), 0.5, places=3)
        stereo = soundpack.read_wav(wav_bytes([0.2, 0.4] * 10, channels=2), 44100)
        self.assertAlmostEqual(float(stereo[0]), 0.3, places=3)

    def test_reinstall_replaces(self):
        soundpack.install_zip(make_zip(self.tmp / "a.zip"), self.packs, 44100)
        soundpack.install_zip(make_zip(self.tmp / "b.zip", manifest=MANIFEST.replace("Test ring", "Renamed")),
                              self.packs, 44100)
        self.assertEqual(soundpack.load("test-ring", self.packs, 44100).name, "Renamed")
        self.assertEqual(sorted(p.name for p in self.packs.iterdir()), ["test-ring"])

    def test_synthetic_is_deterministic_and_round_trips(self):
        a, b = soundpack.synthetic(8, 44100), soundpack.synthetic(8, 44100)
        self.assertTrue(np.array_equal(a.bells[3].samples, b.bells[3].samples))
        self.assertLessEqual(float(np.max(np.abs(a.bells[1].samples))), 0.25 + 1e-6)
        soundpack.write_pack(a, self.tmp / "out", "synth-copy", "Copy")
        loaded = soundpack.load_dir(self.tmp / "out", 44100)
        self.assertEqual(sorted(loaded.bells), list(range(1, 9)))

    def test_load_unknown_pack(self):
        with self.assertRaisesRegex(PackError, "not installed"):
            soundpack.load("nope", self.packs, 44100)
