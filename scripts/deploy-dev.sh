#!/bin/sh
# Dev loop: deploy to the desk Pi *through the release tooling* (design C15),
# never by rsyncing over a live tree, so the update path is exercised on
# every deploy rather than discovered broken in a tower.
#
#   scripts/deploy-dev.sh [pi-host]
#
# Needs: a dev signing key at $TOWER_SIGNING_KEY (default ~/.ssh/tower-release),
# whose public half is in the Pi's /etc/tower/allowed_signers.
set -eu

HOST=${1:-${TOWER_PI:-towerboard.local}}
KEY=${TOWER_SIGNING_KEY:-$HOME/.ssh/tower-release}

cd "$(dirname "$0")/.."
BUNDLE=$(uv run python -m tower.release build --key "$KEY" --out dist | tail -1)
NAME=$(basename "$BUNDLE")
echo "built $NAME"

scp -q "$BUNDLE" "$HOST:/tmp/$NAME"
ssh "$HOST" "chmod a+r /tmp/$NAME && cd /opt/tower/current && \
  sudo -u tower env PYTHONPATH=/opt/tower/current:/opt/tower/current/vendor \
  python3 -m tower.release install /tmp/$NAME && rm -f /tmp/$NAME"

VERSION=${NAME#tower-}
VERSION=${VERSION%.tower}
# Prints the outcome for this version only: ok | failed | in_progress | pending.
RESULT="cd /opt/tower/current && sudo -u tower env PYTHONPATH=/opt/tower/current python3 -m tower.release status \
  | python3 -c 'import json,sys; r=json.load(sys.stdin)[\"last_result\"] or {}; \
print(r.get(\"result\") if r.get(\"version\")==sys.argv[1] else \"pending\")' '$VERSION'"
echo "waiting for the updater…"
i=0
OUT=pending
while [ $i -lt 60 ]; do
  sleep 3
  OUT=$(ssh "$HOST" "$RESULT" 2>/dev/null || echo pending)
  case "$OUT" in ok|failed) break ;; esac
  i=$((i + 1))
done
ssh "$HOST" "sudo journalctl -u tower-update.service -n 20 --no-pager"
echo "update to $VERSION: $OUT"
[ "$OUT" = ok ]
