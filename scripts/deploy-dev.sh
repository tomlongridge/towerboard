#!/bin/sh
# Dev loop: deploy to the desk Pi *through the release tooling* (design C15),
# never by rsyncing over a live tree, so the update path is exercised on
# every deploy rather than discovered broken in a tower.
#
#   scripts/deploy-dev.sh [user@pi-host]      (or: make deploy PI=user@pi-host)
#
# Needs: a signing key at $TOWER_SIGNING_KEY (default ~/.ssh/tower-release),
# whose public half is in the Pi's /etc/tower/allowed_signers. Key-based SSH
# login to the Pi (ssh-copy-id) avoids password prompts.
set -eu

HOST=${1:-${PI:-${TOWER_PI:-ringer@towerboard.local}}}
KEY=${TOWER_SIGNING_KEY:-$HOME/.ssh/tower-release}
START=$(date +%s)

# One SSH connection for the whole deploy: faster, and at most one password prompt.
CONTROL="$HOME/.ssh/tower-deploy-%r@%h:%p"
SSH_OPTS="-o ControlMaster=auto -o ControlPath=$CONTROL -o ControlPersist=120"
pi() { ssh $SSH_OPTS "$HOST" "$@"; }

cd "$(dirname "$0")/.."
BUNDLE=$(uv run python -m tower.release build --key "$KEY" --out dist | tail -1)
NAME=$(basename "$BUNDLE")
VERSION=${NAME#tower-}
VERSION=${VERSION%.tower}
echo "built $VERSION"

scp -q $SSH_OPTS "$BUNDLE" "$HOST:/tmp/$NAME"
# -t: sudo may need to ask for your password (once per deploy).
ssh -t $SSH_OPTS "$HOST" "chmod a+r /tmp/$NAME && cd /opt/tower/current && \
  sudo -u tower env PYTHONPATH=/opt/tower/current:/opt/tower/current/vendor \
  python3 -m tower.release install /tmp/$NAME && rm -f /tmp/$NAME"

# Wait for the updater's verdict on *this* version, read from the public
# diagnostics page over HTTP: no sudo, no SSH. The app restarts during the
# update, so failed requests just mean "not yet".
URL="http://${HOST#*@}/api/diagnostics"
verdict() {
  curl -s --max-time 3 "$URL" | python3 -c '
import json, sys
try:
    r = json.load(sys.stdin)["update"]["last_result"] or {}
except Exception:
    print("pending"); sys.exit()
if r.get("version") == sys.argv[1] and r.get("result") in ("ok", "failed"):
    print(r["result"] + "\t" + (r.get("detail") or ""))
else:
    print("pending")' "$VERSION"
}
echo "waiting for the Pi to restart and health-check…"
i=0
OUT=pending
while [ $i -lt 90 ]; do
  sleep 2
  OUT=$(verdict)
  case "$OUT" in ok*|failed*) break ;; esac
  i=$((i + 1))
done
RESULT=$(printf '%s' "$OUT" | cut -f1)
DETAIL=$(printf '%s' "$OUT" | cut -s -f2)
echo "update to $VERSION: $RESULT ($(( $(date +%s) - START )) s)"
[ -n "$DETAIL" ] && [ "$RESULT" != ok ] && echo "  $DETAIL"
[ "$RESULT" = pending ] && echo "  no verdict yet: check $URL or run 'make logs'"
[ "$RESULT" = ok ]
