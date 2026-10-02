"""Release identity: semantic version plus git SHA (design C15).

A built release carries ``RELEASE.json`` at its root. A source checkout has
none and reports ``<version>+dev``.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from tower import __version__

RELEASE_FILE = "RELEASE.json"


def release_root() -> Path:
    return Path(__file__).resolve().parent.parent


@lru_cache(maxsize=1)
def info() -> dict[str, Any]:
    try:
        manifest = json.loads((release_root() / RELEASE_FILE).read_text())
    except FileNotFoundError:
        return {"version": f"{__version__}+dev", "git_sha": None, "built": None}
    return {k: manifest.get(k) for k in ("version", "git_sha", "built")}


def full_version() -> str:
    return info()["version"]
