"""Finding and downloading releases, against a fake GitHub API."""

import io
import json
import ssl
import tempfile
import unittest
import urllib.error
from pathlib import Path

from tower.release.github import GitHubReleases, UpdateError, is_newer, semver_key

API = "https://api.github.test"


def release(tag, prerelease=False, draft=False, asset=True, body="notes", size=None, data=b"bundle"):
    r = {"tag_name": tag, "prerelease": prerelease, "draft": draft, "body": body,
         "published_at": "2026-10-03T12:00:00Z", "assets": []}
    if asset:
        r["assets"].append({"name": f"tower-{tag.lstrip('v')}.tower", "size": len(data) if size is None else size,
                            "browser_download_url": f"https://github.test/dl/{tag}.tower"})
    return r


class FakeGitHub:
    """Answers like api.github.com and the asset download host."""

    def __init__(self, releases=(), assets=None, error=None):
        self.releases = list(releases)
        self.assets = assets or {}
        self.error = error
        self.requests = []

    def __call__(self, req, timeout):
        self.requests.append(req)
        if self.error:
            raise self.error
        url = req.full_url
        if url.startswith(f"{API}/repos/owner/repo/releases"):
            return io.BytesIO(json.dumps(self.releases).encode())
        if url in self.assets:
            return io.BytesIO(self.assets[url])
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)


def client(fake):
    return GitHubReleases("owner/repo", api=API, opener=fake)


class VersionTest(unittest.TestCase):
    def test_ordering(self):
        order = ["0.9.9", "1.0.0-rc.1", "1.0.0-rc.2", "1.0.0", "1.0.1", "1.10.0", "2.0.0"]
        keys = [semver_key(v) for v in order]
        self.assertEqual(keys, sorted(keys))

    def test_build_metadata_ignored(self):
        self.assertFalse(is_newer("0.3.0", "0.3.0+gbd1bc4c.dirty.20261003121500"))
        self.assertTrue(is_newer("0.3.1", "0.3.0+dev"))
        self.assertFalse(is_newer("0.2.9", "0.3.0+g1a2b3c4"))

    def test_not_semver(self):
        self.assertIsNone(semver_key("latest"))
        self.assertFalse(is_newer("nightly", "0.3.0"))


class LatestTest(unittest.TestCase):
    def test_newest_newer_release_with_a_bundle(self):
        fake = FakeGitHub([release("v0.4.0"), release("v0.5.0", asset=False), release("v0.4.1"),
                           release("v0.3.0"), release("v9.0.0", draft=True), release("v0.6.0-rc.1", prerelease=True)])
        r = client(fake).latest("0.3.0+g1a2b3c4")
        self.assertEqual(r.version, "0.4.1")
        self.assertEqual(r.asset_url, "https://github.test/dl/v0.4.1.tower")
        self.assertEqual(fake.requests[0].get_header("User-agent"), "towerboard-updater")

    def test_pre_release_channel(self):
        fake = FakeGitHub([release("v0.4.0"), release("v0.5.0-rc.1", prerelease=True)])
        self.assertEqual(client(fake).latest("0.3.0", include_pre=True).version, "0.5.0-rc.1")

    def test_up_to_date(self):
        self.assertIsNone(client(FakeGitHub([release("v0.3.0")])).latest("0.3.0+dev"))

    def test_skips_versions_that_failed_here(self):
        fake = FakeGitHub([release("v0.4.0"), release("v0.5.0")])
        self.assertEqual(client(fake).latest("0.3.0", skip={"0.5.0"}).version, "0.4.0")

    def test_errors_are_explained(self):
        cases = [
            (urllib.error.HTTPError("u", 404, "Not Found", {}, None), "not found"),
            (urllib.error.HTTPError("u", 403, "Forbidden", {"X-RateLimit-Remaining": "0"}, None), "limit"),
            (urllib.error.HTTPError("u", 500, "Server Error", {}, None), "500"),
            (urllib.error.URLError(OSError("Network is unreachable")), "cannot reach GitHub"),
            (urllib.error.URLError(ssl.SSLCertVerificationError(1, "certificate is not yet valid")), "clock"),
            (TimeoutError("timed out"), "cannot reach GitHub"),
        ]
        for error, words in cases:
            with self.subTest(error=error), self.assertRaisesRegex(UpdateError, words):
                client(FakeGitHub(error=error)).latest("0.3.0")


class DownloadTest(unittest.TestCase):
    def setUp(self):
        self.dest = Path(tempfile.mkdtemp()) / "in" / "x.tower"

    def test_streams_with_progress(self):
        data = b"x" * 200_000
        rel = release("v0.4.0", data=data)
        fake = FakeGitHub([rel], {"https://github.test/dl/v0.4.0.tower": data})
        r = client(fake).latest("0.3.0")
        seen = []
        client(fake).download(r, self.dest, lambda done, total: seen.append((done, total)))
        self.assertEqual(self.dest.read_bytes(), data)
        self.assertEqual(seen[-1], (200_000, 200_000))

    def test_short_download_rejected_and_removed(self):
        rel = release("v0.4.0", size=1000, data=b"x" * 10)
        fake = FakeGitHub([rel], {"https://github.test/dl/v0.4.0.tower": b"x" * 10})
        r = client(fake).latest("0.3.0")
        with self.assertRaisesRegex(UpdateError, "incomplete"):
            client(fake).download(r, self.dest)
        self.assertFalse(self.dest.exists())

    def test_progress_can_abandon(self):
        rel = release("v0.4.0", data=b"x" * 100)
        fake = FakeGitHub([rel], {"https://github.test/dl/v0.4.0.tower": b"x" * 100})
        r = client(fake).latest("0.3.0")

        def stop(done, total):
            raise KeyboardInterrupt

        with self.assertRaises(KeyboardInterrupt):
            client(fake).download(r, self.dest, stop)
        self.assertFalse(self.dest.exists())
