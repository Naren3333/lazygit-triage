#!/usr/bin/env python3
"""Write the files the agent reads, before the agent starts (workflow step).

Usage:
    python3 prepare_context.py --issue N --repo owner/name [--replay] [--out DIR]

Writes to DIR (default /tmp/gh-aw/triage):
  issue.json          number, title, body, labels, cutoff
  issue-index.json    earlier issues for find_duplicates.py
  releases.json       lazygit releases for check_version.py

Live mode: index = this repo's issues, releases = upstream releases.
Replay mode (golden evals): index/releases come from the frozen files in
evals/golden/context/, and `cutoff` comes from the replay marker, so the
agent never sees anything newer than the original upstream issue.
The agent itself gets no API token for this; it only reads these files.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import replay_marker
from find_duplicates import build_index

UPSTREAM = "jesseduffield/lazygit"
GOLDEN_CONTEXT = Path("evals/golden/context")


def gh_api(path, paginate=False):
    cmd = ["gh", "api", path] + (["--paginate", "--slurp"] if paginate else [])
    data = json.loads(subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", check=True).stdout)
    return [x for page in data for x in page] if paginate else data


def issue_context(issue, replay):
    """Only the fields the agent needs; cutoff honours the replay marker."""
    return {
        "number": issue["number"],
        "title": issue["title"],
        "body": issue.get("body") or "",
        "labels": [l["name"] for l in issue.get("labels", [])],
        "cutoff": replay_marker.effective_created_at(
            issue["created_at"], issue.get("body"), replay),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issue", type=int, required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--replay", action="store_true")
    parser.add_argument("--out", default="/tmp/gh-aw/triage")
    args = parser.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    issue = gh_api(f"repos/{args.repo}/issues/{args.issue}")
    (out / "issue.json").write_text(json.dumps(issue_context(issue, args.replay), indent=1),
                                    encoding="utf-8")

    if args.replay:
        shutil.copy(GOLDEN_CONTEXT / "issue-index.json", out / "issue-index.json")
        shutil.copy(GOLDEN_CONTEXT / "releases.json", out / "releases.json")
    else:
        (out / "issue-index.json").write_text(json.dumps(build_index(args.repo)), encoding="utf-8")
        releases = gh_api(f"repos/{UPSTREAM}/releases?per_page=100", paginate=True)
        slim = [{"tag_name": r["tag_name"], "published_at": r["published_at"]} for r in releases]
        (out / "releases.json").write_text(json.dumps(slim), encoding="utf-8")
    print(f"context written to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
