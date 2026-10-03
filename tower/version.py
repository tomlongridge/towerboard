"""Release identity: semantic version plus git SHA (design C15).

A built release carries ``RELEASE.json`` at its root. A source checkout has
none and reports ``<version>+dev``.

``make hot`` (development only) copies changed files over an installed
release and leaves a ``HOT`` marker holding the time. The version then ends
``.hot.<time>``, so the admin page and diagnostics show the release no longer
matches what was signed, and the wall display reloads for the new code.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from tower import __version__

RELEASE_FILE = "RELEASE.json"
HOT_FILE = "HOT"


def release_root() -> Path:
    return Path(__file__).resolve().parent.parent


@lru_cache(maxsize=1)
def info() -> dict[str, Any]:
    try:
        manifest = json.loads((release_root() / RELEASE_FILE).read_text())
    except FileNotFoundError:
        return {"version": f"{__version__}+dev", "git_sha": None, "built": None, "hot": None}
    result = {k: manifest.get(k) for k in ("version", "git_sha", "built")}
    try:
        hot = (release_root() / HOT_FILE).read_text().strip()
    except FileNotFoundError:
        hot = None
    if hot:
        base = result["version"]
        result["version"] = f"{base}{'.' if '+' in base else '+'}hot.{hot}"
    result["hot"] = hot
    return result


def full_version() -> str:
    return info()["version"]
