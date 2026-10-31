#!/usr/bin/env python3
"""Freeze the upstream context used by golden replays (read-only public API).

Usage:
    python3 evals/golden/build_context.py [--until 2026-10-01T00:00:00Z]

Writes evals/golden/context/:
  issue-index.json  every upstream issue (PRs excluded) created before --until:
                    number, title, body excerpt, created_at. `state` is set
                    to null on purpose: the current state is later knowledge.
  releases.json     upstream releases: tag_name, published_at.

Leakage control: find_duplicates.py / check_version.py filter both files by
the case's created_at at query time. Residual leakage: titles/bodies may
have been edited after the case date (see README.md).
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

UPSTREAM = "jesseduffield/lazygit"
OUT = Path(__file__).resolve().parent / "context"
BODY_EXCERPT = 2000


def gh_pages(path):
    out = subprocess.run(["gh", "api", "--paginate", "--slurp", path],
                         capture_output=True, text=True, encoding="utf-8", check=True).stdout
    return [item for page in json.loads(out) for item in page]


def slim_issues(raw, until):
    return sorted(
        ({"number": i["number"], "title": i["title"],
          "body": (i.get("body") or "")[:BODY_EXCERPT],
          "created_at": i["created_at"], "state": None}
         for i in raw if "pull_request" not in i and i["created_at"] < until),
        key=lambda i: i["number"])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--until", default="2026-10-01T00:00:00Z")
    args = parser.parse_args(argv)

    OUT.mkdir(parents=True, exist_ok=True)
    issues = slim_issues(gh_pages(f"repos/{UPSTREAM}/issues?state=all&per_page=100"), args.until)
    (OUT / "issue-index.json").write_text(json.dumps(issues, indent=0), encoding="utf-8")
    releases = [{"tag_name": r["tag_name"], "published_at": r["published_at"]}
                for r in gh_pages(f"repos/{UPSTREAM}/releases?per_page=100")]
    (OUT / "releases.json").write_text(json.dumps(releases, indent=1), encoding="utf-8")
    print(f"{len(issues)} issues, {len(releases)} releases -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
