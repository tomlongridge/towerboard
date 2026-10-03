"""Writing state so that a power cut cannot leave it empty or half-written.

Towers lose power without warning, and the SD card's filesystem (ext4)
delays writing file contents. Renaming a fresh temporary file into place is
atomic, but unless the data is forced to the card first, a power cut just
after can leave the new file empty. So: write, fsync the file, rename, then
fsync the directory so the rename itself survives.
"""

from __future__ import annotations

import os
from pathlib import Path


def atomic_write(path: Path, data: str | bytes, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = data.encode() if isinstance(data, str) else data
    tmp = path.with_name(f".{path.name}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
    try:
        os.write(fd, raw)
        os.fchmod(fd, mode)  # O_CREAT's mode is reduced by the umask
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(tmp, path)
    fsync_dir(path.parent)


def fsync_dir(path: Path) -> None:
    """Make renames and new entries in ``path`` durable."""
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
