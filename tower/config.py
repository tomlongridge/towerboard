"""Config loading (design C17).

Layers, later wins:

1. Shipped defaults (``DEFAULTS`` below).
2. Tower config, TOML, ``/etc/tower/tower.toml`` (or ``$TOWER_CONFIG``).
3. Runtime overrides set through the UI, JSON, ``/var/lib/tower/overrides.json``
   (or ``$TOWER_OVERRIDES``).
4. Command-line flags.

Only layers 2 and 3 survive an update; neither lives inside a release.
Missing files are not an error, so a Mac with no ``/etc/tower`` runs on defaults.

Unknown keys are logged and ignored rather than rejected: after a rollback,
an older release must still boot against config written for a newer one.
Wrong types are rejected.
"""

from __future__ import annotations

import copy
import dataclasses
import json
import logging
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

log = logging.getLogger(__name__)

TOWER_CONFIG_PATH = Path("/etc/tower/tower.toml")
OVERRIDES_PATH = Path("/var/lib/tower/overrides.json")

SOURCE_KINDS = ("synthetic",)  # serial: M2, replay: M3
LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class TowerSection:
    name: str = "Unconfigured tower"


@dataclass(frozen=True)
class SourceSection:
    kind: str = "synthetic"


@dataclass(frozen=True)
class SyntheticSection:
    bells: int = 8
    gap_ms: float = 200.0
    uplift_ms: float = 200.0
    error_ms: float = 10.0
    latency_ms: float = 2.0
    jitter_ms: float = 1.0
    rows: int = 0  # 0 runs forever
    seed: int = 0


@dataclass(frozen=True)
class LogSection:
    level: str = "INFO"


@dataclass(frozen=True)
class Config:
    tower: TowerSection = field(default_factory=TowerSection)
    source: SourceSection = field(default_factory=SourceSection)
    synthetic: SyntheticSection = field(default_factory=SyntheticSection)
    log: LogSection = field(default_factory=LogSection)


DEFAULTS: dict[str, dict[str, Any]] = {
    f.name: dataclasses.asdict(f.default_factory()) for f in dataclasses.fields(Config)
}


def load(
    tower_path: Path | None = None,
    overrides_path: Path | None = None,
    cli: Mapping[str, Mapping[str, Any]] | None = None,
) -> Config:
    tower_path = tower_path or Path(os.environ.get("TOWER_CONFIG", TOWER_CONFIG_PATH))
    overrides_path = overrides_path or Path(os.environ.get("TOWER_OVERRIDES", OVERRIDES_PATH))

    merged = copy.deepcopy(DEFAULTS)
    _merge(merged, _read_toml(tower_path), str(tower_path))
    _merge(merged, _read_json(overrides_path), str(overrides_path))
    _merge(merged, cli or {}, "command line")
    return _build(merged)


def _read_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        return {}
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"{path}: {e}") from None


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as e:
        raise ConfigError(f"{path}: {e}") from None
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: top level must be an object")
    return data


def _merge(base: dict[str, dict[str, Any]], layer: Mapping[str, Any], origin: str) -> None:
    for section, values in layer.items():
        if section not in base:
            log.warning("%s: ignoring unknown section [%s]", origin, section)
            continue
        if not isinstance(values, Mapping):
            raise ConfigError(f"{origin}: [{section}] must be a table")
        for key, value in values.items():
            if key not in base[section]:
                log.warning("%s: ignoring unknown key %s.%s", origin, section, key)
                continue
            expected = type(base[section][key])
            if not _type_ok(value, expected):
                raise ConfigError(
                    f"{origin}: {section}.{key} must be {expected.__name__}, got {value!r}"
                )
            base[section][key] = expected(value)


def _type_ok(value: Any, expected: type) -> bool:
    if isinstance(value, bool):
        return expected is bool
    if expected is float:
        return isinstance(value, (int, float))
    return isinstance(value, expected)


def _build(merged: dict[str, dict[str, Any]]) -> Config:
    cfg = Config(
        tower=TowerSection(**merged["tower"]),
        source=SourceSection(**merged["source"]),
        synthetic=SyntheticSection(**merged["synthetic"]),
        log=LogSection(**merged["log"]),
    )
    if cfg.source.kind not in SOURCE_KINDS:
        raise ConfigError(f"source.kind must be one of {SOURCE_KINDS}, got {cfg.source.kind!r}")
    if cfg.log.level.upper() not in LOG_LEVELS:
        raise ConfigError(f"log.level must be one of {LOG_LEVELS}, got {cfg.log.level!r}")
    return cfg
