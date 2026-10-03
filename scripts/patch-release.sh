#!/bin/sh
# Bump the patch version (0.4.0 → 0.4.1), commit and push it, then publish:
#
#   make patch-release
#
# Everything is checked before anything changes, and you're asked to confirm.
# If publishing then fails, the bump is already committed and pushed (but no tag
# or release exists): fix the problem and run `make release` to publish it.
set -eu

fail() { echo "error: $*" >&2; exit 1; }
cd "$(dirname "$0")/.."

[ -z "$(git status --porcelain)" ] || fail "commit or stash your changes first"
[ "$(git branch --show-current)" = main ] || fail "releases are published from main"
git fetch -q origin main --tags
[ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] || fail "main differs from GitHub: push or pull first"

OLD=$(uv run python -c 'import tower; print(tower.__version__)')
NEW=$(python3 -c '
import re, sys
m = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", sys.argv[1])
if not m:
    sys.exit(f"error: {sys.argv[1]} is not a plain X.Y.Z version; set __version__ by hand and use make release")
print(f"{m[1]}.{m[2]}.{int(m[3]) + 1}")' "$OLD")

if git rev-parse -q --verify "refs/tags/v$NEW" >/dev/null || gh release view "v$NEW" >/dev/null 2>&1; then
  fail "v$NEW is already published"
fi

echo "running the tests…"
uv run python -m unittest discover -s tests >/dev/null 2>&1 || fail "the tests fail: run make test"

NOTE=""
git rev-parse -q --verify "refs/tags/v$OLD" >/dev/null || NOTE=" ($OLD was never published; use 'make release' to publish it instead)"
printf "Bump %s → %s, commit, push and publish?%s [y/N] " "$OLD" "$NEW" "$NOTE"
read -r answer
case "$answer" in y|Y|yes) ;; *) echo "nothing changed"; exit 1 ;; esac

python3 - "$OLD" "$NEW" <<'PY'
import sys
from pathlib import Path
old, new = sys.argv[1:]
p = Path("tower/__init__.py")
s = p.read_text()
before = f'__version__ = "{old}"'
assert s.count(before) == 1, f"expected exactly one {before} in {p}"
p.write_text(s.replace(before, f'__version__ = "{new}"'))
PY
git commit -q -m "Release v$NEW" tower/__init__.py
git push -q origin main
echo "committed and pushed: Release v$NEW"

# The tests passed on the commit before; only the version line has changed since.
TOWER_SKIP_TESTS=1 scripts/publish-release.sh
