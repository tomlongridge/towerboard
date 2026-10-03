"""Signed release bundles (design C15).

A bundle is one file, ``tower-<version>.tower``, so a phone can carry it as a
single upload. It is an uncompressed tar holding exactly two members:

* ``payload.tar.gz`` — the release tree under ``release/``: ``tower/``,
  ``vendor/`` (pure-Python dependencies), ``deploy/`` and ``RELEASE.json``.
* ``payload.tar.gz.sig`` — an OpenSSH signature (``ssh-keygen -Y sign``,
  namespace ``tower-release``) over the payload.

Signatures use OpenSSH rather than a Python crypto library because the
stdlib has no Ed25519, and ``ssh-keygen`` ships on both the Mac and the Pi.
Verification uses an ``allowed_signers`` file baked into the image, never one
shipped inside a release.

``RELEASE.json`` lists a SHA-256 for every file, so after the signature
check the unpacked tree is checked against it: nothing missing, nothing extra.
"""

from __future__ import annotations

import gzip
import hashlib
import importlib.util
import io
import json
import re
import shutil
import subprocess
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Iterable

NAMESPACE = "tower-release"
PRINCIPAL = "tower-release"
PAYLOAD = "payload.tar.gz"
SIGNATURE = PAYLOAD + ".sig"
MANIFEST_SCHEMA = 1
VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.+-]+)?$")

# Pure-Python runtime dependencies copied into vendor/. Keep in step with pyproject.toml.
VENDOR = ("segno", "serial")  # pyserial imports as `serial`
MAX_PAYLOAD_BYTES = 200 * 1024 * 1024


class ReleaseError(Exception):
    """A bundle was rejected or a release step failed."""


# --- build (Mac) -------------------------------------------------------------


def git_version(src: Path, base: str) -> tuple[str, str | None]:
    """``0.2.0+g1a2b3c4`` (``.dirty`` if the tree has changes), or ``0.2.0`` outside git."""
    try:
        sha = _git(src, "rev-parse", "--short=7", "HEAD")
    except (OSError, subprocess.CalledProcessError):
        return base, None
    # Untracked files count: the build includes everything under these trees.
    dirty = bool(_git(src, "status", "--porcelain", "--", "tower", "deploy"))
    return f"{base}+g{sha}{'.dirty' if dirty else ''}", sha


def _git(src: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=src, check=True, capture_output=True, text=True
    ).stdout.strip()


def collect(src: Path) -> dict[str, Path]:
    """Map of release-relative path → source file."""
    files: dict[str, Path] = {}
    for top in ("tower", "deploy"):
        for p in _tree(src / top):
            files[p.relative_to(src).as_posix()] = p
    for name in VENDOR:
        spec = importlib.util.find_spec(name)
        if spec is None or not spec.submodule_search_locations:
            raise ReleaseError(f"vendored dependency {name!r} is not importable; run `uv sync`")
        pkg = Path(next(iter(spec.submodule_search_locations)))
        for p in _tree(pkg):
            files[f"vendor/{name}/{p.relative_to(pkg).as_posix()}"] = p
    return files


def _tree(root: Path) -> list[Path]:
    """Regular files under ``root``, skipping bytecode and dotfiles such as ``.DS_Store``."""
    return [
        p for p in sorted(root.rglob("*"))
        if p.is_file() and p.suffix != ".pyc"
        and not any(part == "__pycache__" or part.startswith(".") for part in p.relative_to(root).parts)
    ]


def build(src: Path, out_dir: Path, key: Path, version: str | None = None) -> Path:
    """Build and sign a bundle from a source checkout. Returns the bundle path."""
    from tower import __version__

    full, sha = (version, None) if version else git_version(src, __version__)
    if not VERSION_RE.match(full):
        raise ReleaseError(f"bad version {full!r}")
    files = collect(src)
    manifest = {
        "schema_version": MANIFEST_SCHEMA,
        "version": full,
        "git_sha": sha,
        "built": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "files": {rel: _sha256(path.read_bytes()) for rel, path in files.items()},
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        payload = Path(tmp, PAYLOAD)
        _write_payload(payload, files, manifest)
        sign(payload, key)
        bundle = out_dir / f"tower-{full}.tower"
        with tarfile.open(bundle, "w", format=tarfile.PAX_FORMAT) as tar:
            for name in (PAYLOAD, SIGNATURE):
                tar.add(Path(tmp, name), arcname=name, filter=_normalise)
    return bundle


def _write_payload(dest: Path, files: dict[str, Path], manifest: dict) -> None:
    with open(dest, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as gz:
        with tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as tar:
            data = (json.dumps(manifest, indent=2) + "\n").encode()
            _add_bytes(tar, "release/RELEASE.json", data)
            for rel, path in files.items():
                _add_bytes(tar, f"release/{rel}", path.read_bytes())


def _add_bytes(tar: tarfile.TarFile, name: str, data: bytes) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mode = 0o644
    tar.addfile(_normalise(info), io.BytesIO(data))


def _normalise(info: tarfile.TarInfo) -> tarfile.TarInfo:
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    info.mtime = 0
    return info


def sign(path: Path, key: Path) -> Path:
    sig = path.with_name(path.name + ".sig")
    sig.unlink(missing_ok=True)
    r = subprocess.run(
        ["ssh-keygen", "-Y", "sign", "-q", "-f", str(key), "-n", NAMESPACE, str(path)],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise ReleaseError(f"signing failed: {r.stderr.strip()}")
    return sig


# --- verify and unpack (Pi) --------------------------------------------------


def verify(payload: Path, sig: Path, allowed_signers: Path) -> None:
    if not allowed_signers.is_file():
        raise ReleaseError(f"no allowed signers file at {allowed_signers}")
    with payload.open("rb") as f:
        r = subprocess.run(
            ["ssh-keygen", "-Y", "verify", "-f", str(allowed_signers), "-I", PRINCIPAL,
             "-n", NAMESPACE, "-s", str(sig)],
            stdin=f, capture_output=True, text=True,
        )
    if r.returncode != 0:
        detail = (r.stderr or r.stdout).strip() or "bad signature"
        raise ReleaseError(f"signature check failed: {detail}")


def open_bundle(bundle: Path, work: Path, allowed_signers: Path) -> Path:
    """Split ``bundle`` into ``work`` and verify it. Returns the verified payload path."""
    try:
        with tarfile.open(bundle, "r:") as tar:
            members = tar.getmembers()
            names = sorted(m.name for m in members)
            if names != sorted([PAYLOAD, SIGNATURE]) or not all(m.isfile() for m in members):
                raise ReleaseError(f"not a tower bundle (members: {names})")
            for m in members:
                if m.size > MAX_PAYLOAD_BYTES:
                    raise ReleaseError(f"{m.name} is too large")
                src = tar.extractfile(m)
                assert src is not None
                with src, open(work / m.name, "wb") as dst:
                    shutil.copyfileobj(src, dst)
    except tarfile.TarError as e:
        raise ReleaseError(f"not a tower bundle: {e}") from None
    verify(work / PAYLOAD, work / SIGNATURE, allowed_signers)
    return work / PAYLOAD


def read_manifest(payload: Path) -> dict:
    with tarfile.open(payload, "r:gz") as tar:
        try:
            f = tar.extractfile("release/RELEASE.json")
        except KeyError:
            raise ReleaseError("payload has no RELEASE.json") from None
        assert f is not None
        manifest = json.loads(f.read())
    if manifest.get("schema_version") != MANIFEST_SCHEMA:
        raise ReleaseError(f"unsupported manifest schema {manifest.get('schema_version')!r}")
    if not VERSION_RE.match(str(manifest.get("version", ""))):
        raise ReleaseError(f"bad version {manifest.get('version')!r}")
    return manifest


def extract(payload: Path, dest: Path, manifest: dict) -> None:
    """Unpack ``release/`` into ``dest`` and check it against the manifest.

    Members are checked by hand rather than trusting ``tarfile`` filters,
    which Bookworm's 3.11 may predate: regular files and directories only,
    relative paths under ``release/`` only.
    """
    expected: dict[str, str] = manifest["files"]
    seen: set[str] = set()
    dest.mkdir(parents=True)
    with tarfile.open(payload, "r:gz") as tar:
        for m in tar:
            rel = _safe_relpath(m.name)
            if m.isdir():
                (dest / rel).mkdir(parents=True, exist_ok=True)
                continue
            if not m.isfile():
                raise ReleaseError(f"refusing non-regular member {m.name!r}")
            if rel != "RELEASE.json" and rel not in expected:
                raise ReleaseError(f"file not in manifest: {rel}")
            f = tar.extractfile(m)
            assert f is not None
            data = f.read()
            if rel != "RELEASE.json" and _sha256(data) != expected[rel]:
                raise ReleaseError(f"checksum mismatch: {rel}")
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            seen.add(rel)
    missing = set(expected) - seen
    if missing:
        raise ReleaseError(f"files missing from payload: {', '.join(sorted(missing)[:5])}")


def _safe_relpath(name: str) -> str:
    p = PurePosixPath(name)
    if p.is_absolute() or ".." in p.parts or not p.parts or p.parts[0] != "release":
        raise ReleaseError(f"unsafe path in payload: {name!r}")
    rel = PurePosixPath(*p.parts[1:]).as_posix()
    if rel in ("", "."):
        return "."
    return rel


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_allowed_signers(pubkeys: Iterable[str], dest: Path) -> None:
    """Helper for image builds and tests: one ``tower-release <key>`` line per key."""
    dest.write_text("".join(f"{PRINCIPAL} {k.strip()}\n" for k in pubkeys))
