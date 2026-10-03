#!/bin/sh
# First install on a fresh Raspberry Pi OS (Trixie) image. Run as root:
#
#   sudo sh install.sh tower-<version>.tower allowed_signers
#
# Set TOWER_KIOSK=0 to skip the belfry display (a Pi with no monitor).
#
# Every later update goes through the update pipeline (admin page upload, or
# `python3 -m tower.release install`), never through this script.
#
# Safe to run again: if it stopped partway, fix the cause and rerun it with
# the same bundle.
set -eu

if [ $# -ne 2 ]; then
  echo "usage: sudo sh install.sh tower-<version>.tower allowed_signers" >&2
  echo "(got $# arguments: if tower-*.tower matched several bundles, name one)" >&2
  exit 2
fi
BUNDLE=$(realpath "$1")
SIGNERS=$(realpath "$2")
OPT=/opt/tower
STATE=/var/lib/tower
ETC=/etc/tower

[ "$(id -u)" -eq 0 ] || { echo "run as root" >&2; exit 1; }
command -v nmcli >/dev/null || { echo "NetworkManager (nmcli) is required" >&2; exit 1; }

# Verify the bundle before doing anything else.
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
tar -xf "$BUNDLE" -C "$WORK"
ssh-keygen -Y verify -f "$SIGNERS" -I tower-release -n tower-release \
  -s "$WORK/payload.tar.gz.sig" < "$WORK/payload.tar.gz"
mkdir "$WORK/x"
tar -xzf "$WORK/payload.tar.gz" -C "$WORK/x"

# Always install with the installer from inside the (just verified) bundle, so
# installer and release can never come from different versions.
BUNDLED="$WORK/x/release/deploy/install.sh"
if [ -f "$BUNDLED" ] && ! cmp -s "$0" "$BUNDLED" && [ "${TOWER_INSTALLER_REEXEC:-0}" != 1 ]; then
  echo "Using the installer from the bundle."
  INSTALLER=$(mktemp)
  cp "$BUNDLED" "$INSTALLER"
  rm -rf "$WORK"
  TOWER_INSTALLER_REEXEC=1 exec sh "$INSTALLER" "$BUNDLE" "$SIGNERS"
fi
VERSION=$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["version"])' \
  "$WORK/x/release/RELEASE.json")

# C extensions come from Debian, never from the bundle (design §3, §6).
apt-get install -y --no-install-recommends python3-numpy python3-alsaaudio
KIOSK=${TOWER_KIOSK:-1}
if [ "$KIOSK" = 1 ]; then
  # The belfry display: a one-app compositor and a browser, no desktop.
  apt-get install -y --no-install-recommends cage chromium curl
fi

# The default network mode turns wlan0 into the ringers' access point as soon
# as the app starts. If this session arrived over that WiFi, it would drop.
if nmcli -t -f DEVICE,STATE device | grep -q '^wlan0:connected' \
   && ! grep -qs '^\[network\]' "$ETC/tower.toml" \
   && [ "${TOWER_ALLOW_AP_TAKEOVER:-0}" != 1 ]; then
  cat >&2 <<MSG
wlan0 is connected to a WiFi network, and the default network mode will turn it
into an access point, dropping any session that came in over it. Either:
  - configure the network first in $ETC/tower.toml, e.g. to stay on this WiFi:
      [network]
      mode = "joined"
      uplink_ssid = "..."
      uplink_psk = "..."
  - or accept the takeover: TOWER_ALLOW_AP_TAKEOVER=1 sh install.sh ...
MSG
  exit 1
fi

id tower >/dev/null 2>&1 || useradd --system --home-dir "$STATE" --shell /usr/sbin/nologin tower
usermod -aG audio,dialout tower
install -d -o tower -g tower -m 755 "$OPT" "$OPT/releases"
install -d -o tower -g tower -m 750 "$STATE"
install -d -m 755 "$ETC"
install -m 644 "$SIGNERS" "$ETC/allowed_signers"

# Use the bundle's own release tooling to stage it and point `current` at it.
chmod -R a+rX "$WORK"
cp "$BUNDLE" "$WORK/bundle.tower"
chmod a+r "$WORK/bundle.tower"

run_tower() {
  runuser -u tower -- env PYTHONPATH="$WORK/x/release:$WORK/x/release/vendor" \
    python3 -m tower.release "$@"
}
if [ "$(readlink "$OPT/current" 2>/dev/null)" = "releases/$VERSION" ]; then
  echo "$VERSION is already installed; continuing with system setup."
else
  run_tower stage "$WORK/bundle.tower" >/dev/null
  run_tower activate "$VERSION" --no-restart
fi

for unit in tower.service tower-rt.service tower-update.service; do
  install -m 644 "$OPT/current/deploy/systemd/$unit" /etc/systemd/system/
done
install -m 644 "$OPT/current/deploy/polkit/50-tower.rules" /etc/polkit-1/rules.d/
install -m 644 "$OPT/current/deploy/udev/99-tower-serial.rules" /etc/udev/rules.d/
install -m 644 "$OPT/current/deploy/tmpfiles/tower.conf" /etc/tmpfiles.d/
# Whether the access point shares the internet: written by the app (as tower),
# read by the dnsmasq NetworkManager runs for the AP.
install -d -m 755 /etc/NetworkManager/dnsmasq-shared.d
[ -f /etc/NetworkManager/dnsmasq-shared.d/tower-ap.conf ] || : > /etc/NetworkManager/dnsmasq-shared.d/tower-ap.conf
chown tower:tower /etc/NetworkManager/dnsmasq-shared.d/tower-ap.conf
chmod 644 /etc/NetworkManager/dnsmasq-shared.d/tower-ap.conf
systemd-tmpfiles --create /etc/tmpfiles.d/tower.conf
udevadm control --reload && udevadm trigger --subsystem-match=usb-serial
if [ "$KIOSK" = 1 ]; then
  # Its own unprivileged user: the browser gets none of the app's rights.
  id tower-kiosk >/dev/null 2>&1 || useradd --system --create-home --home-dir /var/lib/tower-kiosk \
    --shell /usr/sbin/nologin tower-kiosk
  usermod -aG video,render,input tower-kiosk
  install -m 644 "$OPT/current/deploy/pam/tower-kiosk" /etc/pam.d/tower-kiosk
  install -m 644 "$OPT/current/deploy/systemd/tower-kiosk.service" /etc/systemd/system/
fi
systemctl daemon-reload
systemctl enable --now tower-rt.service tower.service
if [ "$KIOSK" = 1 ]; then
  systemctl enable --now tower-kiosk.service
fi

echo "Installed $VERSION. Open http://<pi-address>/#/admin to set the admin PIN."
