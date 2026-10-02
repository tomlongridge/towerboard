"""Application process (design §1.4): ``python -m tower serve``.

``--dev`` runs from ``./.dev`` on port 8080 so the Mac needs no ``/etc`` or
``/var`` setup. Everything systemd- or NetworkManager-shaped reports itself
unavailable there rather than being faked.
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import threading
from pathlib import Path
from typing import Sequence

from tower import config, migrate, version
from tower.clock import SystemClock
from tower.web.api import TowerApp
from tower.web.server import make_server

log = logging.getLogger("tower.app")

DEV_DIR = Path(".dev")


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m tower serve")
    p.add_argument("--config", type=Path, help=f"tower config (default {config.TOWER_CONFIG_PATH})")
    p.add_argument("--overrides", type=Path, help=f"runtime overrides (default {config.OVERRIDES_PATH})")
    p.add_argument("--host", help="bind address")
    p.add_argument("--port", type=int, help="HTTP port")
    p.add_argument("--dev", action="store_true",
                   help="run from ./.dev on port 8080 (config .dev/tower.toml)")
    args = p.parse_args(argv)
    logging.basicConfig(stream=sys.stderr, level=logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")

    cli: dict[str, dict] = {}
    tower_path, overrides_path = args.config, args.overrides
    if args.dev:
        dev = DEV_DIR.resolve()
        tower_path = tower_path or dev / "tower.toml"
        overrides_path = overrides_path or dev / "state" / "overrides.json"
        cli["paths"] = {"state_dir": str(dev / "state"), "opt_dir": str(dev / "opt")}
        cli["web"] = {"port": 8080}
        cli["update"] = {"allowed_signers": str(dev / "allowed_signers")}
    web = {k: v for k, v in (("host", args.host), ("port", args.port)) if v is not None}
    if web:
        cli["web"] = {**cli.get("web", {}), **web}

    try:
        cfg = config.load(tower_path=tower_path, overrides_path=overrides_path, cli=cli)
    except config.ConfigError as e:
        log.error("%s", e)
        return 2
    logging.getLogger().setLevel(cfg.log.level.upper())

    for mid in migrate.run(cfg.state_dir):
        log.info("applied migration %s", mid)

    app = TowerApp(cfg, SystemClock(), overrides_path=overrides_path)
    _ensure_network(app)
    try:
        server = make_server(app.routes(), cfg.web.host, cfg.web.port)
    except OSError as e:
        log.error("cannot listen on %s:%d: %s", cfg.web.host, cfg.web.port, e)
        return 1

    signal.signal(signal.SIGTERM, lambda *_: threading.Thread(target=server.shutdown).start())
    log.info("tower %s serving %s on http://%s:%d/", version.full_version(), cfg.tower.name,
             cfg.web.host, cfg.web.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def _ensure_network(app: TowerApp) -> None:
    """Bring up the configured mode on first boot; leave it alone if already in effect.

    Re-applying on every start would drop ringers off the AP at each update.
    """
    if not app.net.available():
        log.info("nmcli not available; network management disabled on this host")
        return
    try:
        if app.net.in_effect():
            return
    except RuntimeError as e:
        log.warning("could not read network state: %s", e)
    threading.Thread(target=app.apply_network, name="net-apply", daemon=True).start()
