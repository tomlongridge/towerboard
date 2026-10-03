#!/bin/sh
# First install on a fresh Raspberry Pi OS (Bookworm) image. Run as root:
#
#   sudo sh install.sh tower-<version>.tower allowed_signers
#
# Every later update goes through the update pipeline (admin page upload, or
# `python3 -m tower.release install`), never through this script.
set -eu

BUNDLE=$(realpath "$1")
SIGNERS=$(realpath "$2")
OPT=/opt/tower
STATE=/var/lib/tower
ETC=/etc/tower

[ "$(id -u)" -eq 0 ] || { echo "run as root" >&2; exit 1; }
command -v nmcli >/dev/null || { echo "NetworkManager (nmcli) is required" >&2; exit 1; }

# C extensions come from Debian, never from the bundle (design §3, §6).
apt-get install -y --no-install-recommends python3-numpy python3-alsaaudio

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

# Verify the bundle with the signers just installed, then use its own release
# tooling to stage and point `current` at it.
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
tar -xf "$BUNDLE" -C "$WORK"
ssh-keygen -Y verify -f "$ETC/allowed_signers" -I tower-release -n tower-release \
  -s "$WORK/payload.tar.gz.sig" < "$WORK/payload.tar.gz"
mkdir "$WORK/x"
tar -xzf "$WORK/payload.tar.gz" -C "$WORK/x"
chmod -R a+rX "$WORK"
cp "$BUNDLE" "$WORK/bundle.tower"
chmod a+r "$WORK/bundle.tower"

run_tower() {
  runuser -u tower -- env PYTHONPATH="$WORK/x/release:$WORK/x/release/vendor" \
    python3 -m tower.release "$@"
}
VERSION=$(run_tower stage "$WORK/bundle.tower")
run_tower activate "$VERSION" --no-restart

for unit in tower.service tower-rt.service tower-update.service; do
  install -m 644 "$OPT/current/deploy/systemd/$unit" /etc/systemd/system/
done
install -m 644 "$OPT/current/deploy/polkit/50-tower.rules" /etc/polkit-1/rules.d/
install -m 644 "$OPT/current/deploy/udev/99-tower-serial.rules" /etc/udev/rules.d/
install -m 644 "$OPT/current/deploy/tmpfiles/tower.conf" /etc/tmpfiles.d/
systemd-tmpfiles --create /etc/tmpfiles.d/tower.conf
udevadm control --reload && udevadm trigger --subsystem-match=usb-serial
systemctl daemon-reload
systemctl enable --now tower-rt.service tower.service

echo "Installed $VERSION. Open http://<pi-address>/#/admin to set the admin PIN."
