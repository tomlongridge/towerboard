"""Shared test fixtures: signing keys and bundles built from this checkout."""

import io
import subprocess
import tarfile
import tempfile
from functools import lru_cache
from pathlib import Path

from tower.release import bundle

ROOT = Path(__file__).resolve().parent.parent


def make_key(directory: Path, name: str = "key") -> tuple[Path, Path]:
    """An ed25519 key and an allowed_signers file trusting it."""
    key = directory / name
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True)
    signers = directory / f"{name}.signers"
    bundle.write_allowed_signers([(directory / f"{name}.pub").read_text()], signers)
    return key, signers


@lru_cache(maxsize=None)
def _keys() -> tuple[Path, Path, Path]:
    d = Path(tempfile.mkdtemp(prefix="tower-keys-"))
    key, signers = make_key(d)
    other, _ = make_key(d, "other")
    return key, signers, other


def signing_key() -> Path:
    return _keys()[0]


def allowed_signers() -> Path:
    return _keys()[1]


def untrusted_key() -> Path:
    return _keys()[2]


def build_bundle(out: Path, version: str, key: Path | None = None) -> Path:
    return bundle.build(ROOT, out, key or signing_key(), version=version)


def craft_bundle(out: Path, members: dict[str, bytes], manifest: dict | None, key: Path | None = None) -> Path:
    """A signed bundle with arbitrary payload members, for attacks the builder never makes."""
    payload = out / bundle.PAYLOAD
    with tarfile.open(payload, "w:gz") as tar:
        entries = dict(members)
        if manifest is not None:
            import json

            entries = {"release/RELEASE.json": json.dumps(manifest).encode(), **entries}
        for name, data in entries.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    bundle.sign(payload, key or signing_key())
    path = out / "crafted.tower"
    with tarfile.open(path, "w") as tar:
        tar.add(payload, arcname=bundle.PAYLOAD)
        tar.add(out / bundle.SIGNATURE, arcname=bundle.SIGNATURE)
    return path
