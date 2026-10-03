#!/bin/sh
# Allow hot deploys without a password, on a development Pi:
#
#   make hot-setup        (asks for your Pi password once)
#   make hot-teardown     removes it
#
# Lets your Pi user run exactly the three commands scripts/hot-deploy.sh needs,
# and nothing else, without a password: copy its holding folder into the
# installed release, write the HOT marker, restart the app. That still means
# you can put code on the Pi that runs as the `tower` user (that's the point),
# so never do this on a Pi going into a tower.
set -eu

HOST=${1:-${PI:-${TOWER_PI:-ringer@towerboard.local}}}
ACTION=${2:-setup}
RULES=/etc/sudoers.d/tower-hot

if [ "$ACTION" = teardown ]; then
  ssh -t "$HOST" "sudo rm -f $RULES && echo 'removed: hot deploys will ask for a password again'"
  exit 0
fi

# Built on the Pi, where the user name and home directory are known. sudo needs
# '=' and ':' in command arguments escaped. The commands must match hot-deploy.sh exactly.
ssh -t "$HOST" 'set -eu
command -v rsync >/dev/null || { echo "rsync is needed first: sudo apt install rsync" >&2; exit 1; }
user=$(id -un)
tmp=$(mktemp)
cat > "$tmp" <<RULES
# Towerboard hot deploys (make hot, make watch) for $user. Development Pi only.
# Remove with: make hot-teardown
Cmnd_Alias TOWER_HOT_COPY = /usr/bin/rsync -a --delete --chown\\=tower\\:tower --exclude __pycache__ $HOME/.tower-hot/ /opt/tower/current/tower/
Cmnd_Alias TOWER_HOT_RESTART = /usr/bin/systemctl restart tower.service, /usr/bin/systemctl restart tower.service tower-rt.service
$user ALL=(root) NOPASSWD: TOWER_HOT_COPY, TOWER_HOT_RESTART
$user ALL=(tower) NOPASSWD: /usr/bin/tee /opt/tower/current/HOT
RULES
sudo visudo -cf "$tmp" >/dev/null
sudo install -m 440 -o root -g root "$tmp" '"$RULES"'
rm -f "$tmp"
sudo -k
sudo -n -l /usr/bin/systemctl restart tower.service >/dev/null && echo "done: make hot and make watch no longer need a password"'
