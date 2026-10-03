#!/bin/sh
# Hot deploy, for trying small changes on the desk Pi in seconds:
#
#   make hot          once
#   make watch        on every save (needs `make hot-setup` once)
#
# Copies the changed files under tower/ over the release that is installed,
# then restarts the app (and the sound process only if its code changed).
# Development only: no tests, no signature, no health check, no rollback. The
# installed release no longer matches what was signed, so its version gains
# ".hot.<time>" (shown on the admin page). The next `make deploy` or update
# replaces it with a real release.
#
# The three root commands below are also what `make hot-setup` allows without
# a password, so they must stay identical (sudo matches them exactly).
set -eu

HOST=${1:-${PI:-${TOWER_PI:-ringer@towerboard.local}}}
NONINTERACTIVE=${HOT_NONINTERACTIVE:-0}
START=$(date +%s)
CONTROL="$HOME/.ssh/tower-deploy-%r@%h:%p"
SSH_OPTS="-o ControlMaster=auto -o ControlPath=$CONTROL -o ControlPersist=600"

# Run on the Pi, where $HOME is the Pi user's home.
COPY='/usr/bin/rsync -a --delete --chown=tower:tower --exclude __pycache__ $HOME/.tower-hot/ /opt/tower/current/tower/'
MARK='/usr/bin/tee /opt/tower/current/HOT'
RESTART='/usr/bin/systemctl restart'

cd "$(dirname "$0")/.."

# 1. Changed files to a holding folder in your home directory on the Pi (no sudo needed).
CHANGES=$(rsync -a --delete --itemize-changes --exclude __pycache__ --exclude '*.pyc' \
  -e "ssh $SSH_OPTS" tower/ "$HOST:.tower-hot/" | grep -E '^[<>ch*]' || true) \
  || { echo "error: could not copy to $HOST (is rsync installed on the Pi? sudo apt install rsync)" >&2; exit 1; }
if [ -z "$CHANGES" ]; then
  echo "nothing changed since the last hot deploy"
  exit 0
fi
echo "$CHANGES" | sed -E 's/^[^ ]+ /  /'

# 2. The sound process imports only these; restart it only if one of them changed
#    (it takes longer, and stops any bells sounding).
UNITS=tower.service
if echo "$CHANGES" | awk '{print $2}' | grep -qE '^(rt/|config\.py|events\.py|ipc\.py|clock\.py|fsutil\.py|version\.py|__init__\.py)'; then
  UNITS="tower.service tower-rt.service"
fi

# 3. Into the installed release, mark it hot, restart. Without a password if
#    `make hot-setup` was run; otherwise sudo asks (not possible under `make watch`).
STAMP=$(date -u +%Y%m%d%H%M%S)
REMOTE="sudo -n $COPY && echo $STAMP | sudo -n -u tower $MARK >/dev/null && sudo -n $RESTART $UNITS"
if ssh $SSH_OPTS "$HOST" "sudo -n -l $RESTART tower.service" >/dev/null 2>&1; then
  ssh $SSH_OPTS "$HOST" "$REMOTE"  # allowed without a password: errors are real, so show them
elif [ "$NONINTERACTIVE" = 1 ]; then
  echo "error: the Pi needs a password for this. Run 'make hot-setup' once to allow hot deploys without one." >&2
  exit 1
else
  ssh -t $SSH_OPTS "$HOST" "$(echo "$REMOTE" | sed 's/sudo -n /sudo /g')"
fi

# 4. Wait for the app to answer again.
URL="http://${HOST#*@}/api/health"
i=0
while [ $i -lt 30 ]; do
  sleep 1
  if V=$(curl -s --max-time 2 "$URL" | python3 -c 'import json,sys; print(json.load(sys.stdin)["version"])' 2>/dev/null); then
    echo "running $V ($(( $(date +%s) - START )) s; restarted $UNITS)"
    exit 0
  fi
  i=$((i + 1))
done
echo "the app hasn't come back: run 'make logs' to see why, or 'make deploy' to install a real release" >&2
exit 1
