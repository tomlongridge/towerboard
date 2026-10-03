"""Hot-deploy to the Pi on every save: ``make watch`` (Ctrl-C to stop).

Polls tower/ once a second (nothing to install), waits until edits have
settled, then runs scripts/hot-deploy.sh. Needs ``make hot-setup`` once, so
deploys don't stop to ask for a password.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WATCHED = ROOT / "tower"
POLL_S = 1.0
SETTLE_S = 0.8  # editors and formatters write in bursts


def snapshot() -> dict[str, tuple[float, int]]:
    out = {}
    for p in WATCHED.rglob("*"):
        if "__pycache__" in p.parts or p.suffix == ".pyc" or p.name.startswith("."):
            continue
        try:
            st = p.stat()
        except FileNotFoundError:
            continue  # deleted mid-scan
        if p.is_file():
            out[str(p.relative_to(ROOT))] = (st.st_mtime, st.st_size)
    return out


def deploy(host: str) -> bool:
    env = {**os.environ, "HOT_NONINTERACTIVE": "1"}
    return subprocess.run([str(ROOT / "scripts" / "hot-deploy.sh"), host], cwd=ROOT, env=env).returncode == 0


def main() -> int:
    host = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("PI", "")
    if not host:
        print("usage: watch.py user@pi-host", file=sys.stderr)
        return 2
    print(f"watching {WATCHED.relative_to(ROOT)}/ → {host} (Ctrl-C to stop)")
    if not deploy(host):  # bring the Pi in line first, and fail early if hot-setup is missing
        return 1
    seen = snapshot()
    try:
        while True:
            time.sleep(POLL_S)
            now = snapshot()
            if now == seen:
                continue
            while True:  # wait for the burst of writes to finish
                time.sleep(SETTLE_S)
                settled = snapshot()
                if settled == now:
                    break
                now = settled
            changed = sorted(k for k in now.keys() | seen.keys() if now.get(k) != seen.get(k))
            seen = now
            print(f"\n{time.strftime('%H:%M:%S')} changed: {', '.join(changed[:5])}"
                  + (f" and {len(changed) - 5} more" if len(changed) > 5 else ""))
            if not deploy(host):
                print("deploy failed; fix and save again (still watching)")
    except KeyboardInterrupt:
        print("\nstopped watching")
        return 0


if __name__ == "__main__":
    sys.exit(main())
