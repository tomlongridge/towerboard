"""Entry point: ``python -m tower``.

    python -m tower serve [--dev]          application process: web app and admin
    python -m tower rt [--dev]             real-time process: sensor → strike → audio
    python -m tower rt-jitter --capture …  audio timing gate (desk Pi, loopback cable)
    python -m tower --source=synthetic     pulse pipeline, envelopes to stdout
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Sequence

from tower import config, pipeline, version
from tower.clock import Clock, FakeClock, SystemClock
from tower.events import SCHEMA_VERSION
from tower.rt.source import PulseSource

log = logging.getLogger("tower")


def build_source(cfg: config.Config, clock: Clock) -> tuple[PulseSource, str]:
    from tower.rt.main import build_source as rt_build_source

    return rt_build_source(cfg, cfg.source.kind, clock)


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="python -m tower",
        description="Run the tower pipeline, writing event envelopes to stdout as JSON lines.",
    )
    p.add_argument("--source", choices=config.SOURCE_KINDS, help="pulse source (default from config)")
    p.add_argument("--config", type=Path, help=f"tower config (default {config.TOWER_CONFIG_PATH})")
    p.add_argument("--overrides", type=Path, help=f"runtime overrides (default {config.OVERRIDES_PATH})")
    p.add_argument("--rows", type=int, help="synthetic: stop after this many rows (0 = forever)")
    p.add_argument("--bells", type=int, help="synthetic: number of bells")
    p.add_argument("--seed", type=int, help="synthetic: random seed")
    p.add_argument(
        "--fast",
        action="store_true",
        help="use a fake clock: run as fast as possible with deterministic output",
    )
    p.add_argument("--version", action="version", version=f"tower {version.full_version()} (events v{SCHEMA_VERSION})")
    return p.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["serve"]:
        from tower import app

        return app.main(argv[1:])
    if argv[:1] == ["rt"]:
        from tower.rt import main as rt

        return rt.main(argv[1:])
    if argv[:1] == ["rt-jitter"]:
        from tower.rt import jitter

        return jitter.main(argv[1:])
    return run_pipeline(argv)


def run_pipeline(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    logging.basicConfig(stream=sys.stderr, format="%(levelname)s %(name)s: %(message)s")

    cli: dict[str, dict] = {}
    if args.source:
        cli["source"] = {"kind": args.source}
    synthetic = {k: v for k in ("rows", "bells", "seed") if (v := getattr(args, k)) is not None}
    if synthetic:
        cli["synthetic"] = synthetic

    try:
        cfg = config.load(tower_path=args.config, overrides_path=args.overrides, cli=cli)
        logging.getLogger().setLevel(cfg.log.level.upper())
        clock: Clock = FakeClock() if args.fast else SystemClock()
        source, source_name = build_source(cfg, clock)
    except (config.ConfigError, ValueError) as e:
        log.error("%s", e)
        return 2

    log.info("tower %s: %s, source=%s", version.full_version(), cfg.tower.name, cfg.source.kind)
    try:
        n = pipeline.run(source, sys.stdout, source_name)
    except KeyboardInterrupt:
        return 130
    except BrokenPipeError:
        # Downstream closed (e.g. `| head`); not an error.
        sys.stdout = None  # type: ignore[assignment]  # suppress flush-at-exit error
        return 0
    log.info("emitted %d events", n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
