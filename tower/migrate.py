"""State migrations against ``/var/lib/tower`` (design C15 step 4).

Forward-only and idempotent. Each migration runs at most once, recorded in
``migrations.json``; running one twice must still be harmless, because a
power cut can land between the work and the record. An older release
must tolerate state migrated by a newer one, as rollback never migrates down.

Run by the update pipeline from the *new* release::

    python -m tower.migrate --state-dir /var/lib/tower
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Callable

RECORD = "migrations.json"


def _0001_state_layout(state: Path) -> None:
    for sub in ("sessions", "incoming"):
        (state / sub).mkdir(parents=True, exist_ok=True)


MIGRATIONS: list[tuple[str, Callable[[Path], None]]] = [
    ("0001_state_layout", _0001_state_layout),
]


def applied(state: Path) -> list[str]:
    try:
        return json.loads((state / RECORD).read_text())["applied"]
    except FileNotFoundError:
        return []


def run(state: Path) -> list[str]:
    """Apply pending migrations in order. Returns the ids applied this run."""
    state.mkdir(parents=True, exist_ok=True)
    done = applied(state)
    ran = []
    for mid, fn in MIGRATIONS:
        if mid in done:
            continue
        fn(state)
        done.append(mid)
        ran.append(mid)
        tmp = state / (RECORD + ".tmp")
        tmp.write_text(json.dumps({"applied": done}, indent=2) + "\n")
        os.replace(tmp, state / RECORD)
    return ran


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m tower.migrate")
    p.add_argument("--state-dir", type=Path, required=True)
    args = p.parse_args(argv)
    for mid in run(args.state_dir):
        print(f"applied {mid}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
