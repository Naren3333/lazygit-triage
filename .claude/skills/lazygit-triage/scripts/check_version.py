#!/usr/bin/env python3
"""Is the lazygit version in an issue too far behind the latest release?

Usage:
    python3 check_version.py --text "<version string or issue body>" \
        --as-of 2026-05-03T10:00:00Z [--releases releases.json] [--max-behind 3]

releases.json: [{"tag_name": "v0.56.0", "published_at": "2026-..Z"}, ...]
(the shape of GET /repos/jesseduffield/lazygit/releases). Only releases
published before --as-of count, so replays never see future releases.

Prints JSON: {"found": "v0.32.2", "latest": "v0.56.0", "minors_behind": 24,
"too_old": true}. "found" is null when no version is present.
Always exits 0 on valid input: this is information, the skill decides.
"""
import argparse
import json
import re
import sys
from pathlib import Path

DEFAULT_RELEASES = Path("/tmp/gh-aw/triage/releases.json")
# Matches "v0.56.0", "0.56", and `lazygit version` output "version=0.56.0".
VERSION_RE = re.compile(r"(?:version=|\bv)?(\d+)\.(\d+)(?:\.(\d+))?\b")
LAZYGIT_HINT_RE = re.compile(r"version=(\d+)\.(\d+)(?:\.(\d+))?")


def parse_version(text):
    """Return (major, minor, patch) for the most specific lazygit version in text."""
    match = LAZYGIT_HINT_RE.search(text) or _first_plausible(text)
    if not match:
        return None
    major, minor, patch = match.groups()
    return int(major), int(minor), int(patch or 0)


def _first_plausible(text):
    # lazygit is 0.x; skip things like "Ubuntu 24.04" or "git 2.43".
    for match in VERSION_RE.finditer(text):
        if match.group(1) == "0":
            return match
    return None


def latest_as_of(releases, as_of):
    """Highest released version published strictly before as_of (ISO strings)."""
    versions = [parse_version(r["tag_name"]) for r in releases
                if r.get("published_at") and r["published_at"] < as_of]
    versions = [v for v in versions if v]
    return max(versions) if versions else None


def check(text, releases, as_of, max_behind=3):
    found = parse_version(text)
    latest = latest_as_of(releases, as_of)
    result = {"found": _fmt(found), "latest": _fmt(latest),
              "minors_behind": None, "too_old": False}
    if found and latest and found[0] == latest[0]:
        behind = max(0, latest[1] - found[1])
        result["minors_behind"] = behind
        result["too_old"] = behind > max_behind
    return result


def _fmt(version):
    return "v%d.%d.%d" % version if version else None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text", required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--releases", default=DEFAULT_RELEASES)
    parser.add_argument("--max-behind", type=int, default=3)
    args = parser.parse_args(argv)

    releases = json.loads(Path(args.releases).read_text(encoding="utf-8"))
    print(json.dumps(check(args.text, releases, args.as_of, args.max_behind)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
