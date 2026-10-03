# Towerboard

## Mission

A belfry-based ringing simulator / "strikometer" controlled by mobile devices, but displayed to the tower, with additional news/information shown when idle.

## Feature overview

* Easy to install
* Connectivity through mobile web interface
* Simulator for selecting computer-powered bells
* Striking analyser (strikometer) for analysing human ringing
* Historical record of touches
* News, events, performances and statistics information board

## Technology overview

Towerboard runs on a Raspberry Pi in the belfry, which is connected to sensors on the bells for striking data, and to a monitor in the belfy for display. It is designed to be controlled, configured and updated entirely using mobile devices rather than an awkward keyboard and mouse setup. This is achieved by hosting an access point (AP) on the Pi to which users connect and can access a hosted web app to control the system.

One key aspect of the design is that internet connectivity is usually very limited in towers. The system therefore works with _optional_ internet access for updating its software and content: attempting to use configured mobile hotspots or falling back to a USB stick if an offline update is required.

## Hardware requirements

* Raspberry Pi version 4 Model or later
* Speakers (USB or bluetooth)
* [Bagley simulator](http://www.bagleybells.co.uk/sensors/sensors.htm) or similar
* Monitor (micro HDMI)

## Installation and updates

### Installation

The initial image for the system is supplied on an SD card with a default SSID and password. All further updates and configuration are applied by connected users to the AP network. The first user to register automatically becomes an admin with access to the Admin Control Panel (ACP).

### Internet access

The system ideally has two network cards, one of them WiFi: to allow simultaneous connection to the internet for receiving updates as well as hosting a local network for users. However, it also allows for a single network option: with the app looking for a configured set of SSIDs to connect to. If not found, or connection is lost, the system switches to AP mode until rebooted. If there is no content to download, or it has completed, the system switches to AP mode.

When in update mode, the monitor displays a message instructing users of the progress of any updates being downloaded and what to do if it gets stuck (restart and disable named networks).

### Software updates

Towerboard releases are hosted on GitHub - this detected at startup and downloaded, with an option in the ACP to apply the update.

## Features

### Bell sounds

The system is connected to sensors on the bells via a serial to USB interface. Whenever a strike is detected, the system will play the sound of the associated bell. These sound files are in a known location in the filesystem and can be uploaded by connecting to the Pi's file system or via the web app.

### Simulated touches

Users can select a touch for the system to "ring" where one or more of the bells can be omitted and rung by a real ringer to allow practices when there are fewer ringers around.

### Touch detection and recording

Touches can either be initiated manually, with a user selecting a method, or automatically when two whole pulls (i.e. handstroke and backstroke twice) of rounds has been sounded on 3 or more bells. Full touch details are available for 24 hours, configurable via the web app, for striking analysis and replay.

### Strikometer

Using the Hawkear algorithm, the striking of a touch can be analysed to give whole-band and per-ringer details of striking. This can be enabled and disabled for each touch.

## Web app

The Pi hosts a web app which is used by both the belfry monitor and connected users. These will be called "interactive" and "kiosk" mode in the documentation.

If the `?kiosk=true` querystring is passed in, the app enters "kiosk" mode and the display is automatically controlled without authentication. Otherwise the user is prompted for a username/password or to create an account. If the user decides to continue without logging in, they can access the Information screens only.

### Kiosk mode

In kiosk mode (i.e. the belfy display), the app cycles through the information screens to show notices, an events calendar, Bellboard performances and tower information. The pages shown and the length of display of a page, is configured in the ACP.

The cycle of pages is interrupted if a bell strike is detected – when this occurs, the Active Ringing page is shown until there has been a pause in ringing for 30 seconds (configurable via the ACP)

### AP footer

The footer of all screens shows the SSID of the AP network, the password and the address of the web app.

## Information screens

### Notices

Displays a list of active notices for the tower, which can be clicked on to see the details, consisting of:

* Title
* Content (HTML)
* Images

Admin users are able to add, edit, delete and archive notices. Archived notices are not shown, but can be accessed via the ACP.

In kiosk mode, each active notice is shown individually: text first and then full page images.

### Calendar

Displays a list of future events, by month, which can be clicked on to see the details, consisting of:

* Title
* Date
* Time (from / to)
* Content (HTML)

Admin users are able to add, edit and delete events. Past events are not shown, but can be accessed via the ACP.

In kiosk mode, each active event is shown individually.

### Performances

Displays a curated list of performances from Bellboard (bb.ringingworld.co.uk), which can be clicked on to see the details, consisting of:

* Date
* Tower
* Changes and method
* Images

Admin users are able to add (via URL) and delete performances. If no internet connection is available, new performances are fetched during the next update.

Admin users can also setup a filter in the ACP, which interfaces with the BellBoard search page to automatically show performances. These cannot be removed on this page, but are managed in the ACP.

### Tower information

Displays a static information page about the tower and bells, taken from Dove's Guide (dove.cccbr.org.uk) using the ID in the ACP.

### Welcome information

A welcome message to ringers in the belfry.

### Active ringing

Displays each bell number in a box - either coloured or white depending on whether it's at handstroke or backstroke - to give a visual indication of the ringing going on.

If a touch has been initiated, the current method is displayed.

In interactive mode, the following controls are available:

* Reset handstroke/backstroke state - all bells return to handstroke position
* Start / stop / reset the touch - if a touch has been initiated
* Enable/disable Strikometer

### Update mode information

Displays status of an update in-progress, including the steps to take to recover if the update fails (e.g. internet connectivity fails on connected device).

## User screens

### New touch

Allows a user to select a method for the next touch. This might be for all-humans or partly computer-rung.

Users select:

* a method - filtering on name, stage and type (Surprise, Delight, etc)
* which bells are human-controlled and which are rung by the simulator - with convenience button to make all-human
* peal speed - i.e. the speed of the ringing, if >0 computer ringers
* manual start/stop or number of whole pulls (hand + backstroke) before the method starts/ends

A button is shown to initiate the touch.

### Recent touch list

Each touch is fully stored in the system for 24 hours. The touch list shows all the touches and allows users to select one to enter the Touch Details page.

### Touch details

Displays the full details of a touch, including:

* Method and changes

### Last touch

### Ringer touch details

### Ringer stats

## Control screens

Available in interactive mode only:

### Admin control panel (ACP)

* Reboot to update mode
* Apply update
* SSID list, including add and remove
* Set AP SSID name and password
* GitHub releases URL
* User password reset and removal
* Admin user list
* Kiosk mode screens and speed
* Delay before returning to information screen cycle after ringing
* Archived notice / event list - unarchive and delete options
* BellBoard performance filters - including setting a relative from date
* Tower details page - name, Dove ID, colour scheme and welcome message
* Bell sounds - upload per bell
* Touch retention period
* Whether Strikometer is enabled by default

## Component design detail

### Database

Local persistence on the Pi is provided by a local Postgres database.

### Sound and calibration

Sound packs are zips holding `manifest.toml` and one WAV per bell (format in [tower/rt/soundpack.py](tower/rt/soundpack.py)), uploaded on the admin page. Until one is installed, the Pi sounds synthetic bells generated in code.

To calibrate, ring open with the bells sounding and use the admin page's calibration table to nudge each bell's handstroke and backstroke in 5 ms steps until the sound lands with the real bell. Offsets are stored per tower in `/var/lib/tower/calibration.json`, never in the sound pack.

Before releasing anything that touches the audio path, run the jitter gate on the desk Pi with a loopback cable from the output to a capture input. It plays 3,000 clicks and fails if any lands more than 10 ms from where it was scheduled:

```bash
python3 -m tower rt-jitter --device plughw:CARD=Headphones --capture plughw:CARD=Device --blows 3000
```

To capture a golden byte stream from the real photohead box (for decoder tests):

```bash
python3 -m tower.rt.serial_source --capture box.bin --seconds 60
```

### Releases

Towerboard releases are stored in GitHub and pull down to the system via WiFi (either direct or via a user's device), depending on whether the system contains one or two network cards and whether a WiFi network is reachable.

A release is a ZIP file containing the following:

* The source code bundle
* The latest method definition XML file from the [CCCBR website](http://methods.cccbr.org/)

### Methods

The system maintains a list of methods from the [CCCBR website](http://methods.cccbr.org/), which are downloaded as part of a release. They are parsed and stored during the release installation and made available to system components.

### Touches

For each touch, the following is recorded:

* Method - if selected in New Touch screen
* Changes - the number of rows rung
  * The system should start counting once two non-rounds rows have been rung and stop counting when two rows of rounds have been rung again, the first rounds should not be included in the count, but all others should
* The bells rung and which were computer controlled
* The claimed bells - bells which users have claimed as themselves, and wheher they were a conductor
* Striking data - the full data from the Stikometer, if enabled
* Striking summary - band- and ringer-level summarised data from the Strikometer, if enabled
## Development

The consolidated design and milestone plan is in [tower-system-design.md](tower-system-design.md).

Python is pinned to the Pi's shipped interpreter in `.python-version` (Bookworm: 3.11). Use `uv` so the Mac runs the same version:

```bash
uv sync
```

### Running locally

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

### Config

Layers, later wins: shipped defaults → `/etc/tower/tower.toml` (`$TOWER_CONFIG`) → `/var/lib/tower/overrides.json` (`$TOWER_OVERRIDES`, written by the admin page) → command-line flags. Missing files are fine. Example `tower.toml`:

```toml
[tower]
name = "St Mary"

[network]
mode = "ap"            # ap | joined | dual
ap_ssid = "St Mary bells"
ap_psk = "ringing-is-fun"
```

### Sound and calibration

Sound packs are zips holding `manifest.toml` and one WAV per bell (format in [tower/rt/soundpack.py](tower/rt/soundpack.py)), uploaded on the admin page. Until one is installed, the Pi sounds synthetic bells generated in code.

To calibrate, ring open with the bells sounding and use the admin page's calibration table to nudge each bell's handstroke and backstroke in 5 ms steps until the sound lands with the real bell. Offsets are stored per tower in `/var/lib/tower/calibration.json`, never in the sound pack.

Before releasing anything that touches the audio path, run the jitter gate on the desk Pi with a loopback cable from the output to a capture input. It plays 3,000 clicks and fails if any lands more than 10 ms from where it was scheduled:

```bash
python3 -m tower rt-jitter --device plughw:CARD=Headphones --capture plughw:CARD=Device --blows 3000
```

To capture a golden byte stream from the real photohead box (for decoder tests):

```bash
python3 -m tower.rt.serial_source --capture box.bin --seconds 60
```

### Releases

Releases are signed with an OpenSSH key and verified on the Pi against `/etc/tower/allowed_signers`. Create a signing key once:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/tower-release -C tower-release
```

Its `allowed_signers` line is `tower-release ` followed by the contents of `~/.ssh/tower-release.pub`. Build a bundle (`dist/tower-<version>.tower`; one file, so a phone can carry it):

```bash
uv run python -m tower.release build --key ~/.ssh/tower-release
```

The bundle vendors its pure-Python dependencies, so the Pi runs it with the system `python3` and never needs network access or pip.

**First install** on a fresh Raspberry Pi OS (Bookworm), as root, with the bundle and the `allowed_signers` file copied over:

```bash
sudo sh install.sh tower-0.2.0+g1a2b3c4.tower allowed_signers
```

(`install.sh` is in `deploy/` in this repo and in every bundle.) It also installs the Debian packages for the C extensions (`python3-numpy`, `python3-alsaaudio`), the systemd units, the udev rule that sets the USB serial latency timer to 1 ms, and the polkit rule.

**Upgrading from 0.2 (M1) to 0.3 (M2)** needs `install.sh` run once more, because M2 adds system pieces an update cannot install (the `tower-rt.service` unit, Debian packages, udev and polkit rules). Uploading 0.3 to an M1 install through the admin page rolls back automatically, because the health check can't find `tower-rt.service`. It refuses to run if the Pi is on WiFi and no `[network]` config exists, because the default `ap` mode would take over `wlan0` and drop your session.

**Every later update** goes through the update pipeline: upload the bundle on the admin page, or from the Mac:

```bash
scripts/deploy-dev.sh towerboard.local
```

This builds, copies and installs through the same verify → stage → swap → health check → auto-rollback path a tower uses, never by rsyncing over a live tree. Layout on the Pi:

```
/opt/tower/releases/<version>/   unpacked releases
/opt/tower/current, previous     symlinks
/var/lib/tower/                  state (never inside a release)
/etc/tower/                      tower.toml, allowed_signers
```
