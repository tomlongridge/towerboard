"""Sound packs — durable contract 1 (design C4).

A pack is a directory (uploaded as a zip) holding ``manifest.toml`` and one
WAV per bell::

    schema_version = 1
    id = "tower-8-taylor"
    name = "Taylor 8, 12cwt"
    sample_rate = 44100

    [provenance]
    source = "Recorded in the tower, 2026"
    licence = "CC-BY-4.0"

    [[bells]]
    number = 1
    file = "bell01.wav"
    gain_db = 0.0
    strike_offset_ms = { hand = 0, back = 0 }

The design sketched YAML; TOML is used because the stdlib reads it.

Compatibility: ``schema_version`` is bumped only for incompatible changes;
unknown keys are ignored, so packs may carry extra metadata.

``strike_offset_ms`` in a pack covers the recording (silence before the
strike in the sample). Each tower's own sensor-to-strike offsets are
calibrated separately and never written into a pack.

The pack id ``synthetic`` is reserved for bells generated in code, so a
fresh install makes a sound before anyone uploads a real recording.
"""

from __future__ import annotations

import io
import os
import re
import shutil
import tomllib
import wave
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

import numpy as np

SCHEMA_VERSION = 1
SYNTHETIC_ID = "synthetic"
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
MAX_ZIP_BYTES = 128 * 1024 * 1024
MAX_SECONDS_PER_BELL = 12.0
MAX_FILE_BYTES = 24 * 1024 * 1024  # 12 s of 24-bit stereo at 96 kHz is ~7 MB


class PackError(Exception):
    pass


@dataclass
class Bell:
    number: int
    samples: np.ndarray  # float32 mono at the output rate, gain applied
    offset_ms: dict[str, float] = field(default_factory=lambda: {"hand": 0.0, "back": 0.0})


@dataclass
class SoundPack:
    id: str
    name: str
    rate: int
    bells: dict[int, Bell]
    provenance: dict = field(default_factory=dict)

    def summary(self) -> dict:
        return {"id": self.id, "name": self.name, "bells": sorted(self.bells),
                "provenance": self.provenance,
                "seconds": round(sum(len(b.samples) for b in self.bells.values()) / self.rate, 1)}


# --- manifest ----------------------------------------------------------------


def parse_manifest(text: str) -> dict:
    try:
        m = tomllib.loads(text)
    except tomllib.TOMLDecodeError as e:
        raise PackError(f"manifest.toml: {e}") from None
    if m.get("schema_version") != SCHEMA_VERSION:
        raise PackError(f"unsupported schema_version {m.get('schema_version')!r}")
    pid = m.get("id", "")
    if not isinstance(pid, str) or not ID_RE.match(pid) or pid == SYNTHETIC_ID:
        raise PackError(f"bad pack id {pid!r}: lowercase letters, digits and dashes")
    if not isinstance(m.get("name"), str):
        raise PackError("manifest needs a name")
    bells = m.get("bells")
    if not isinstance(bells, list) or not bells:
        raise PackError("manifest needs [[bells]]")
    seen = set()
    for b in bells:
        n = b.get("number")
        if not isinstance(n, int) or not 1 <= n <= 16 or n in seen:
            raise PackError(f"bad or duplicate bell number {n!r}")
        seen.add(n)
        f = b.get("file", "")
        if not isinstance(f, str) or PurePosixPath(f).name != f or not f.lower().endswith(".wav"):
            raise PackError(f"bell {n}: file must be a plain .wav name, got {f!r}")
        if not isinstance(b.get("gain_db", 0.0), (int, float)):
            raise PackError(f"bell {n}: gain_db must be a number")
        off = b.get("strike_offset_ms", {})
        if not isinstance(off, dict) or not all(isinstance(off.get(k, 0), (int, float)) for k in ("hand", "back")):
            raise PackError(f"bell {n}: strike_offset_ms must be {{ hand = .., back = .. }}")
    return m


# --- loading -----------------------------------------------------------------


def read_wav(data: bytes, rate: int) -> np.ndarray:
    """16- or 24-bit PCM WAV → float32 mono at ``rate``."""
    try:
        with wave.open(io.BytesIO(data)) as w:
            width, channels, src_rate, n = w.getsampwidth(), w.getnchannels(), w.getframerate(), w.getnframes()
            raw = w.readframes(n)
    except (wave.Error, EOFError) as e:
        raise PackError(f"not a PCM WAV: {e}") from None
    if n > MAX_SECONDS_PER_BELL * src_rate:
        raise PackError(f"sample longer than {MAX_SECONDS_PER_BELL} s")
    if width == 2:
        x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    elif width == 3:
        b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        v = b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)
        v = np.where(v >= 1 << 23, v - (1 << 24), v)
        x = v.astype(np.float32) / float(1 << 23)
    else:
        raise PackError(f"unsupported sample width {8 * width} bits (use 16 or 24)")
    x = x.reshape(-1, channels).mean(axis=1)
    if src_rate != rate:
        t_out = np.arange(int(len(x) * rate / src_rate)) * (src_rate / rate)
        x = np.interp(t_out, np.arange(len(x)), x).astype(np.float32)
    return np.ascontiguousarray(x, dtype=np.float32)


def load_dir(path: Path, rate: int) -> SoundPack:
    m = parse_manifest((path / "manifest.toml").read_text())
    bells = {}
    for b in m["bells"]:
        try:
            samples = read_wav((path / b["file"]).read_bytes(), rate)
        except FileNotFoundError:
            raise PackError(f"bell {b['number']}: {b['file']} missing") from None
        except PackError as e:
            raise PackError(f"bell {b['number']} ({b['file']}): {e}") from None
        samples *= np.float32(10 ** (float(b.get("gain_db", 0.0)) / 20))
        off = b.get("strike_offset_ms", {})
        bells[b["number"]] = Bell(b["number"], samples,
                                  {"hand": float(off.get("hand", 0)), "back": float(off.get("back", 0))})
    return SoundPack(m["id"], m["name"], rate, bells, m.get("provenance", {}))


def load(pack_id: str, packs_dir: Path, rate: int, bells: int = 16) -> SoundPack:
    if pack_id == SYNTHETIC_ID:
        return synthetic(bells, rate)
    if not ID_RE.match(pack_id):
        raise PackError(f"bad pack id {pack_id!r}")
    path = packs_dir / pack_id
    if not path.is_dir():
        raise PackError(f"sound pack {pack_id!r} is not installed")
    return load_dir(path, rate)


def installed(packs_dir: Path) -> list[dict]:
    out = [{"id": SYNTHETIC_ID, "name": "Synthetic bells (built in)"}]
    if packs_dir.is_dir():
        for d in sorted(packs_dir.iterdir()):
            if d.is_dir() and ID_RE.match(d.name):
                try:
                    m = parse_manifest((d / "manifest.toml").read_text())
                    out.append({"id": m["id"], "name": m["name"], "bells": len(m["bells"])})
                except (OSError, PackError):
                    continue
    return out


# --- install from upload ---------------------------------------------------------


def install_zip(data_path: Path, packs_dir: Path, rate: int) -> SoundPack:
    """Validate an uploaded zip fully (every WAV decodes) before it replaces anything."""
    if data_path.stat().st_size > MAX_ZIP_BYTES:
        raise PackError("sound pack too large")
    try:
        zf = zipfile.ZipFile(data_path)
    except zipfile.BadZipFile:
        raise PackError("not a zip file") from None
    with zf:
        # Packs may be zipped with or without an enclosing folder.
        names = [n for n in zf.namelist() if not n.endswith("/") and "__MACOSX" not in n]
        manifests = [n for n in names if PurePosixPath(n).name == "manifest.toml"]
        if len(manifests) != 1:
            raise PackError("zip must contain exactly one manifest.toml")
        for info in zf.infolist():  # sizes from the directory, before decompressing anything
            if info.file_size > MAX_FILE_BYTES:
                raise PackError(f"{info.filename} is too large")
        prefix = manifests[0][: -len("manifest.toml")]
        if prefix.count("/") > 1:
            raise PackError("manifest.toml must be at the top of the zip or in one folder")
        m = parse_manifest(zf.read(manifests[0]).decode("utf-8", errors="replace"))
        packs_dir.mkdir(parents=True, exist_ok=True)
        staging = packs_dir / f".{m['id']}.staging"
        shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir()
        try:
            (staging / "manifest.toml").write_bytes(zf.read(manifests[0]))
            for b in m["bells"]:
                try:
                    data = zf.read(prefix + b["file"])
                except KeyError:
                    raise PackError(f"bell {b['number']}: {b['file']} missing from zip") from None
                (staging / b["file"]).write_bytes(data)
            pack = load_dir(staging, rate)  # decodes every WAV: proves the pack is usable
            final = packs_dir / m["id"]
            if final.exists():
                old = packs_dir / f".{m['id']}.old"
                shutil.rmtree(old, ignore_errors=True)
                os.rename(final, old)
                os.rename(staging, final)
                shutil.rmtree(old, ignore_errors=True)
            else:
                os.rename(staging, final)
            return pack
        finally:
            shutil.rmtree(staging, ignore_errors=True)


# --- synthetic bells ---------------------------------------------------------------

# Partials of a well-tuned bell, as multiples of the nominal, with relative
# amplitude and decay time (s). Lower partials ring on; the strike fades fast.
_PARTIALS = [
    (0.25, 0.45, 3.0),   # hum
    (0.5, 0.55, 2.0),    # prime
    (0.6, 0.45, 1.6),    # tierce (minor third)
    (0.75, 0.2, 1.2),    # quint
    (1.0, 1.0, 1.1),     # nominal
    (1.5, 0.3, 0.6),     # superquint
    (2.0, 0.25, 0.4),    # octave nominal
    (2.61, 0.12, 0.25),
]
_MAJOR_DOWN = [0, -1, -3, -5, -7, -8, -10, -12, -13, -15, -17, -19, -20, -22, -24, -25]


def synthetic(bells: int, rate: int, treble_hz: float = 1568.0, seconds: float = 2.5) -> SoundPack:
    """A diatonic ring (major scale down from G6), deterministic and generated in code."""
    out = {}
    n = int(seconds * rate)
    t = np.arange(n, dtype=np.float64) / rate
    rng = np.random.default_rng(1)
    for i in range(bells):
        nominal = treble_hz * 2 ** (_MAJOR_DOWN[i] / 12)
        size = 1 + i / max(1, bells - 1)  # bigger bells ring longer
        x = np.zeros(n)
        for ratio, amp, decay in _PARTIALS:
            x += amp * np.sin(2 * np.pi * nominal * ratio * t) * np.exp(-t / (decay * size))
        click = rng.standard_normal(n) * np.exp(-t / 0.004) * 0.3  # clapper transient
        x = (x + click) * (1 - np.exp(-t / 0.0005))  # 0.5 ms attack: no click at sample start
        x *= 0.25 / np.max(np.abs(x))
        out[i + 1] = Bell(i + 1, x.astype(np.float32))
    return SoundPack(SYNTHETIC_ID, f"Synthetic {bells}", rate, out,
                     {"source": "generated by tower.rt.soundpack", "licence": "same as Towerboard"})


def write_pack(pack: SoundPack, dest: Path, pack_id: str, name: str) -> None:
    """Write a loaded pack as a directory (used to make example and test packs)."""
    dest.mkdir(parents=True, exist_ok=True)
    lines = [f"schema_version = {SCHEMA_VERSION}", f'id = "{pack_id}"', f'name = "{name}"',
             f"sample_rate = {pack.rate}", ""]
    for n, bell in sorted(pack.bells.items()):
        fname = f"bell{n:02d}.wav"
        pcm = (np.clip(bell.samples, -1, 1) * 32767).astype("<i2").tobytes()
        with wave.open(str(dest / fname), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(pack.rate)
            w.writeframes(pcm)
        lines += ["[[bells]]", f"number = {n}", f'file = "{fname}"', "gain_db = 0.0",
                  "strike_offset_ms = { hand = 0, back = 0 }", ""]
    (dest / "manifest.toml").write_text("\n".join(lines))
