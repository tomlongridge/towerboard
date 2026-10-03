#!/bin/sh
# Publish a release on GitHub (design C15). Towers find it at their next check,
# download and verify it, and offer it on the admin page.
#
#   make release
#
# Publishes the version in tower/__init__.py. Bump it first; a version is only
# ever published once. Signing happens here, on your machine: the signing key
# never goes to GitHub, and GitHub cannot sign anything a tower will accept.
set -eu

KEY=${TOWER_SIGNING_KEY:-$HOME/.ssh/tower-release}
fail() { echo "error: $*" >&2; exit 1; }

cd "$(dirname "$0")/.."
command -v gh >/dev/null || fail "the GitHub CLI (gh) is needed: brew install gh, then gh auth login"
[ -f "$KEY" ] || fail "no signing key at $KEY"

VERSION=$(uv run python -c 'import tower; print(tower.__version__)')
TAG="v$VERSION"

[ -z "$(git status --porcelain)" ] || fail "commit or stash your changes first: a release is built from a commit"
[ "$(git branch --show-current)" = main ] || fail "releases are published from main"
git fetch -q origin main --tags
[ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] || fail "main differs from GitHub: push or pull first"
if git rev-parse -q --verify "refs/tags/$TAG" >/dev/null || gh release view "$TAG" >/dev/null 2>&1; then
  fail "$TAG is already published: bump __version__ in tower/__init__.py"
fi

echo "running the tests…"
uv run python -m unittest discover -s tests >/dev/null 2>&1 || fail "the tests fail: run make test"

BUNDLE=$(uv run python -m tower.release build --key "$KEY" --out dist | tail -1)
case "$(basename "$BUNDLE")" in
  *dirty*) fail "built from a modified tree" ;;
esac
echo "built $(basename "$BUNDLE")"

# Check it the way a tower will: signature against the public key, every file's checksum.
uv run python - "$BUNDLE" "$KEY.pub" <<'PY'
import sys, tempfile
from pathlib import Path
from tower.release import bundle
work = Path(tempfile.mkdtemp())
signers = work / "allowed_signers"
bundle.write_allowed_signers([Path(sys.argv[2]).read_text()], signers)
payload = bundle.open_bundle(Path(sys.argv[1]), work, signers)
manifest = bundle.read_manifest(payload)
bundle.extract(payload, work / "release", manifest)
print(f"verified {manifest['version']}: {len(manifest['files'])} files")
PY

PRE=""
case "$VERSION" in *-*) PRE="--prerelease" ;; esac

git tag -a "$TAG" -m "Towerboard $VERSION"
git push -q origin "$TAG"
gh release create "$TAG" "$BUNDLE" --title "Towerboard $VERSION" --generate-notes --verify-tag $PRE
echo "published $TAG: towers will offer it at their next check"
