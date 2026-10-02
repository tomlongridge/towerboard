"""Release tooling: ``python -m tower.release <command>``.

On the Mac::

    python -m tower.release build --key ~/.ssh/tower-release

On the Pi (as the ``tower`` user)::

    python -m tower.release install /tmp/tower-0.2.0+g1a2b3c4.tower   # stage + hand to updater
    python -m tower.release status
    python -m tower.release rollback
    python -m tower.release run-request                               # what tower-update.service runs
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from tower import config
from tower.clock import SystemClock
from tower.release import ReleaseError, ReleaseManager, host
from tower.release.bundle import build


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m tower.release")
    p.add_argument("--config", type=Path, help="tower config file")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="build and sign a bundle from this checkout")
    b.add_argument("--key", type=Path, required=True, help="OpenSSH private key used to sign")
    b.add_argument("--out", type=Path, default=Path("dist"))
    b.add_argument("--src", type=Path, default=Path.cwd())

    st = sub.add_parser("stage", help="verify and unpack a bundle without activating it")
    st.add_argument("bundle", type=Path)

    ins = sub.add_parser("install", help="stage a bundle and hand activation to the updater unit")
    ins.add_argument("bundle", type=Path)

    act = sub.add_parser("activate", help="activate a staged release in this process")
    act.add_argument("version")
    act.add_argument("--no-restart", action="store_true",
                     help="first install only: point current without restarting or health-checking")

    sub.add_parser("rollback", help="hand a rollback to the updater unit")
    sub.add_parser("run-request", help="perform a pending request (run by tower-update.service)")
    sub.add_parser("status", help="print release status as JSON")

    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if args.cmd == "build":
        try:
            path = build(args.src.resolve(), args.out, args.key)
        except ReleaseError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        print(path)
        return 0

    cfg = config.load(tower_path=args.config)
    mgr = ReleaseManager(cfg.opt_dir, cfg.state_dir)
    signers = Path(cfg.update.allowed_signers)

    try:
        if args.cmd == "status":
            print(json.dumps(mgr.status(), indent=2))
            return 0
        if args.cmd == "stage":
            print(mgr.stage(args.bundle, signers))
            return 0
        if args.cmd == "install":
            version = mgr.stage(args.bundle, signers)
            host.write_request(cfg.state_dir, "activate", version)
            host.start_updater()
            print(f"staged {version}; activation handed to {host.UPDATER_UNIT}")
            return 0
        if args.cmd == "rollback":
            host.write_request(cfg.state_dir, "rollback")
            host.start_updater()
            print(f"rollback handed to {host.UPDATER_UNIT}")
            return 0
        if args.cmd == "activate" and args.no_restart:
            result = mgr.activate(args.version, restart=lambda: None,
                                  health=lambda v: (True, "not checked (first install)"))
            print(json.dumps(result.as_dict(), indent=2))
            return 0 if result.ok else 1

        restart = host.restart_units(cfg.update.units)
        health = host.health_check(cfg.web.port, cfg.update.units, cfg.update.health_timeout_s,
                                   SystemClock())
        if args.cmd == "activate":
            result = mgr.activate(args.version, restart, health)
        else:  # run-request
            req = host.take_request(cfg.state_dir)
            if req is None:
                print("no pending request")
                return 0
            if req.get("action") == "activate":
                result = mgr.activate(req["version"], restart, health)
            elif req.get("action") == "rollback":
                result = mgr.rollback(restart, health)
            else:
                print(f"error: unknown request {req!r}", file=sys.stderr)
                return 1
        print(json.dumps(result.as_dict(), indent=2))
        return 0 if result.ok else 1
    except (ReleaseError, RuntimeError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
