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
NETWORK_MODES = ("ap", "joined", "dual")


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
class PathsSection:
    state_dir: str = "/var/lib/tower"  # state, never inside a release
    opt_dir: str = "/opt/tower"  # releases/, current, previous


@dataclass(frozen=True)
class WebSection:
    host: str = "0.0.0.0"
    port: int = 80


@dataclass(frozen=True)
class AdminSection:
    session_hours: float = 12.0


@dataclass(frozen=True)
class NetworkSection:
    mode: str = "ap"
    ap_interface: str = "wlan0"  # onboard radio
    ap_ssid: str = "towerboard"
    ap_psk: str = "bellringing"
    uplink_ssid: str = ""
    uplink_psk: str = ""
    join_timeout_s: float = 30.0


@dataclass(frozen=True)
class UpdateSection:
    # OpenSSH allowed_signers file, baked into the image, never shipped in a release.
    allowed_signers: str = "/etc/tower/allowed_signers"
    health_timeout_s: float = 60.0
    units: list = field(default_factory=lambda: ["tower.service"])


@dataclass(frozen=True)
class Config:
    tower: TowerSection = field(default_factory=TowerSection)
    source: SourceSection = field(default_factory=SourceSection)
    synthetic: SyntheticSection = field(default_factory=SyntheticSection)
    log: LogSection = field(default_factory=LogSection)
    paths: PathsSection = field(default_factory=PathsSection)
    web: WebSection = field(default_factory=WebSection)
    admin: AdminSection = field(default_factory=AdminSection)
    network: NetworkSection = field(default_factory=NetworkSection)
    update: UpdateSection = field(default_factory=UpdateSection)

    @property
    def state_dir(self) -> Path:
        return Path(self.paths.state_dir)

    @property
    def opt_dir(self) -> Path:
        return Path(self.paths.opt_dir)


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


def save_overrides(section: str, values: Mapping[str, Any], path: Path | None = None) -> None:
    """Merge ``values`` into the runtime overrides file (layer 3), atomically.

    Validated against the defaults first, so the UI cannot persist a config
    that would stop the next boot.
    """
    if section not in DEFAULTS:
        raise ConfigError(f"unknown section [{section}]")
    path = path or Path(os.environ.get("TOWER_OVERRIDES", OVERRIDES_PATH))
    current = _read_json(path)
    current.setdefault(section, {}).update(values)
    candidate = copy.deepcopy(DEFAULTS)
    _merge(candidate, current, "overrides")
    _build(candidate)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(current, indent=2) + "\n")
    os.chmod(tmp, 0o600)  # may hold WiFi passphrases
    os.replace(tmp, path)


def _build(merged: dict[str, dict[str, Any]]) -> Config:
    sections = {f.name: f.default_factory for f in dataclasses.fields(Config)}
    cfg = Config(**{name: cls(**merged[name]) for name, cls in sections.items()})
    if cfg.source.kind not in SOURCE_KINDS:
        raise ConfigError(f"source.kind must be one of {SOURCE_KINDS}, got {cfg.source.kind!r}")
    if cfg.log.level.upper() not in LOG_LEVELS:
        raise ConfigError(f"log.level must be one of {LOG_LEVELS}, got {cfg.log.level!r}")
    if cfg.network.mode not in NETWORK_MODES:
        raise ConfigError(f"network.mode must be one of {NETWORK_MODES}, got {cfg.network.mode!r}")
    if not 8 <= len(cfg.network.ap_psk) <= 63:
        raise ConfigError("network.ap_psk must be 8..63 characters (WPA2)")
    if not 1 <= len(cfg.network.ap_ssid.encode()) <= 32:
        raise ConfigError("network.ap_ssid must be 1..32 bytes")
    if not all(isinstance(u, str) for u in cfg.update.units):
        raise ConfigError("update.units must be a list of unit names")
    return cfg
