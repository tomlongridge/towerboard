# Development

The consolidated design and milestone plan is in [tower-system-design.md](tower-system-design.md).

Python is pinned to the Pi's shipped interpreter in `.python-version` (Trixie: 3.13). Use `uv` so the Mac runs the same version:

```bash
uv sync
```

## Running locally

The web app and admin, from `./.dev` on port 8080 (no `/etc` or `/var` needed):

```bash
uv run python -m tower serve --dev
```

Open http://localhost:8080/ (`?display=wall` for the belfry display, `#/admin` for admin, `#/diagnostics`). The first visit to admin sets the PIN; delete `.dev/state/admin.json` to start again. systemd and NetworkManager don't exist on the Mac, and the app says so rather than faking them: uploads are verified and staged but only activated on the Pi.

Alongside it, the real-time process (sensor → strike → audio). On the Mac there is no ALSA, so it runs silently but still sends strikes to the app, and the wall display (`?display=wall`) animates:

```bash
uv run python -m tower rt --dev --source synthetic
```

To *hear* the engine on the Mac, render a synthetic touch to a WAV file offline and play it:

```bash
uv run python -m tower rt --render touch.wav --seconds 30
```

```bash
afplay touch.wav
```

The raw pulse pipeline, envelopes to stdout as JSON lines (`--source serial` to watch the real box):

```bash
uv run python -m tower --source=synthetic
```

`--fast` swaps in a fake clock: no real-time pacing and byte-identical output for a given `--seed`.

Tests:

```bash
uv run python -m unittest discover -s tests -v
```

## Config

Layers, later wins: shipped defaults → `/etc/tower/tower.toml` (`$TOWER_CONFIG`) → `/var/lib/tower/overrides.json` (`$TOWER_OVERRIDES`, written by the admin page) → command-line flags. Missing files are fine. Example `tower.toml`:

```toml
[tower]
name = "St Mary"

[network]
mode = "ap"            # ap | joined | dual
ap_ssid = "St Mary bells"
ap_psk = "ringing-is-fun"
```

## Sound and calibration

Sound packs are zips holding `manifest.toml` and one WAV per bell (format in [tower/rt/soundpack.py](../tower/rt/soundpack.py)), uploaded on the admin page. Until one is installed, the Pi sounds synthetic bells generated in code.

To calibrate, ring open with the bells sounding and use the admin page's calibration table to nudge each bell's handstroke and backstroke in 5 ms steps until the sound lands with the real bell. Offsets are stored per tower in `/var/lib/tower/calibration.json`, never in the sound pack.

Before releasing anything that touches the audio path, run the jitter gate on the desk Pi with a loopback cable from the output to a capture input. It plays 3,000 clicks and fails if any lands more than 10 ms from where it was scheduled:

```bash
python3 -m tower rt-jitter --device plughw:CARD=Headphones --capture plughw:CARD=Device --blows 3000
```

To capture a golden byte stream from the real photohead box (for decoder tests):

```bash
python3 -m tower.rt.serial_source --capture box.bin --seconds 60
```

## Releases

Releases are signed with an OpenSSH key and verified on the Pi against `/etc/tower/allowed_signers`. Create a signing key once:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/tower-release -C tower-release
```

Its `allowed_signers` line is `tower-release ` followed by the contents of `~/.ssh/tower-release.pub`. Build a bundle (`dist/tower-<version>.tower`; one file, so a phone can carry it):

```bash
uv run python -m tower.release build --key ~/.ssh/tower-release
```

The bundle vendors its pure-Python dependencies, so the Pi runs it with the system `python3` and never needs network access or pip.

**First install** on a fresh Raspberry Pi OS (Trixie), as root, with the bundle and the `allowed_signers` file copied over:

```bash
sudo sh install.sh tower-0.2.0+g1a2b3c4.tower allowed_signers
```

(`install.sh` is in `deploy/` in this repo and in every bundle.) It also installs the Debian packages for the C extensions (`python3-numpy`, `python3-alsaaudio`), the systemd units, the udev rule that sets the USB serial latency timer to 1 ms, and the polkit rule.

It also sets up the belfry display: `tower-kiosk.service` runs Chromium full screen under `cage` (a compositor that shows one app, no desktop) as an unprivileged `tower-kiosk` user, on the Pi's own monitor, at `http://localhost/?display=wall`. It waits for the app to answer before starting, and the page reloads itself when it sees a new version after an update. `TOWER_KIOSK=0` skips it for a Pi with no monitor. The image is Raspberry Pi OS **Lite**: a desktop session would bring PipeWire, which can hold the sound card the RT process drives directly.

**Upgrading from 0.2 (M1) to 0.3 (M2)** needs `install.sh` run once more, because M2 adds system pieces an update cannot install (the `tower-rt.service` unit, Debian packages, udev and polkit rules). Uploading 0.3 to an M1 install through the admin page rolls back automatically, because the health check can't find `tower-rt.service`. It refuses to run if the Pi is on WiFi and no `[network]` config exists, because the default `ap` mode would take over `wlan0` and drop your session.

**Every later update** goes through the update pipeline: upload the bundle on the admin page, or from the Mac:

```bash
make deploy
```

`make` on its own lists the other tasks (`test`, `serve`, `rt`, `status`, `logs`, …). Put your Pi's address in `local.mk` (not committed) as `PI = ringer@your-pi.local`, and run `make ssh-key` once for password-free login.

The round trip runs the tests, builds a signed release (uncommitted changes get a timestamped version, so every build is distinct), copies it over, installs it through the updater, and waits for the restart and health check. It ends with the result and how long it took. Every deploy restarts the app and sound services: each release is a separate folder and a running process stays pinned to the one it started from. For fast iteration on the web pages, use `make serve` on the Mac and deploy when it's ready.

This builds, copies and installs through the same verify → stage → swap → health check → auto-rollback path a tower uses, never by rsyncing over a live tree. Layout on the Pi:

```
/opt/tower/releases/<version>/   unpacked releases
/opt/tower/current, previous     symlinks
/var/lib/tower/                  state (never inside a release)
/etc/tower/                      tower.toml, allowed_signers
```
