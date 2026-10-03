"""Finding and downloading releases on GitHub (design C15).

Each GitHub release carries the signed ``.tower`` bundle as an asset. GitHub
and HTTPS are only the transport: a downloaded bundle is staged through the
same signature check as an uploaded one, so a compromised GitHub account
cannot put code on a tower without the signing key.

Requests are unauthenticated (the repository is public; the limit of 60 an
hour per address is far above need).
"""

from __future__ import annotations

import json
import re
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from tower.release.bundle import MAX_PAYLOAD_BYTES

API = "https://api.github.com"
USER_AGENT = "towerboard-updater"
SEMVER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?(?:\+.*)?$")
MAX_NOTES = 4000


class UpdateError(Exception):
    """A check or download failed; the message is meant for the admin page."""


@dataclass(frozen=True)
class Release:
    tag: str
    version: str  # from the tag, without the leading "v"
    prerelease: bool
    asset_name: str
    asset_url: str
    size: int
    notes: str
    published_at: str

    def as_dict(self) -> dict:
        return {"tag": self.tag, "version": self.version, "prerelease": self.prerelease,
                "asset": self.asset_name, "size": self.size, "notes": self.notes,
                "published_at": self.published_at}


def semver_key(version: str) -> tuple | None:
    """Sort key for ``1.2.3``, ``v1.2.3-rc.1``, ``1.2.3+g1a2b3c4.dirty…``; None if not semver.

    Build metadata (after ``+``) is ignored, so a development build of 0.3.0 is
    not "older" than the published 0.3.0. A pre-release sorts before its release.
    """
    m = SEMVER_RE.match(version.strip())
    if not m:
        return None
    major, minor, patch, pre = m.groups()
    if pre is None:
        pre_key: tuple = (1,)  # releases after their pre-releases
    else:
        pre_key = (0, tuple((0, int(p)) if p.isdigit() else (1, p) for p in pre.split(".")))
    return (int(major), int(minor), int(patch), pre_key)


def is_newer(candidate: str, current: str) -> bool:
    a, b = semver_key(candidate), semver_key(current)
    return a is not None and (b is None or a > b)


Opener = Callable[[urllib.request.Request, float], object]


def _default_open(req: urllib.request.Request, timeout: float):
    return urllib.request.urlopen(req, timeout=timeout)


class GitHubReleases:
    def __init__(self, repo: str, api: str = API, opener: Opener = _default_open) -> None:
        self.repo = repo
        self.api = api.rstrip("/")
        self.open = opener

    def latest(self, current: str, include_pre: bool = False, skip: set[str] = frozenset()) -> Release | None:
        """The newest release newer than ``current`` with a bundle attached, or None."""
        data = self._get_json(f"{self.api}/repos/{self.repo}/releases?per_page=30")
        best: Release | None = None
        for r in data if isinstance(data, list) else []:
            if r.get("draft") or (r.get("prerelease") and not include_pre):
                continue
            tag = str(r.get("tag_name", ""))
            version = tag[1:] if tag.startswith("v") else tag
            if semver_key(version) is None or version in skip or not is_newer(version, current):
                continue
            asset = next((a for a in r.get("assets", []) if str(a.get("name", "")).endswith(".tower")), None)
            if asset is None:
                continue
            rel = Release(
                tag=tag, version=version, prerelease=bool(r.get("prerelease")),
                asset_name=asset["name"], asset_url=asset["browser_download_url"],
                size=int(asset.get("size", 0)), notes=str(r.get("body") or "")[:MAX_NOTES],
                published_at=str(r.get("published_at", "")),
            )
            if best is None or semver_key(rel.version) > semver_key(best.version):
                best = rel
        return best

    def download(self, release: Release, dest: Path,
                 progress: Callable[[int, int], None] = lambda done, total: None) -> Path:
        """Stream the bundle to ``dest``. ``progress`` may raise to abandon the download."""
        if release.size > MAX_PAYLOAD_BYTES:
            raise UpdateError(f"{release.asset_name} is too large ({release.size} bytes)")
        dest.parent.mkdir(parents=True, exist_ok=True)
        done = 0
        try:
            with self._request(release.asset_url, accept="application/octet-stream", timeout=60) as resp, \
                    open(dest, "wb") as f:
                while chunk := resp.read(1 << 16):
                    done += len(chunk)
                    if done > MAX_PAYLOAD_BYTES:
                        raise UpdateError("download is larger than any release can be")
                    f.write(chunk)
                    progress(done, release.size)
        except BaseException:
            dest.unlink(missing_ok=True)
            raise
        if release.size and done != release.size:
            dest.unlink(missing_ok=True)
            raise UpdateError(f"download incomplete: {done} of {release.size} bytes")
        return dest

    # --- HTTP ---------------------------------------------------------------------

    def _get_json(self, url: str):
        with self._request(url, accept="application/vnd.github+json", timeout=20) as resp:
            try:
                return json.loads(resp.read())
            except ValueError:
                raise UpdateError("GitHub sent something that isn't JSON") from None

    def _request(self, url: str, accept: str, timeout: float):
        req = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": USER_AGENT})
        try:
            return self.open(req, timeout)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise UpdateError(f"GitHub repository {self.repo!r} not found (is it public?)") from None
            if e.code in (403, 429) and e.headers.get("X-RateLimit-Remaining") == "0":
                raise UpdateError("GitHub's limit on checks from this address was reached; try again in an hour") from None
            raise UpdateError(f"GitHub answered {e.code} {e.reason}") from None
        except urllib.error.URLError as e:
            reason = e.reason
            if isinstance(reason, ssl.SSLCertVerificationError):
                why = getattr(reason, "verify_message", None) or reason
                raise UpdateError("secure connection to GitHub failed: the Pi's clock may be wrong "
                                  f"(not yet set from the internet) ({why})") from None
            raise UpdateError(f"cannot reach GitHub: {reason}") from None
        except (TimeoutError, OSError) as e:
            raise UpdateError(f"cannot reach GitHub: {e}") from None
