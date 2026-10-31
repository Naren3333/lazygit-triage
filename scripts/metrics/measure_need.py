#!/usr/bin/env python3
"""Measure the triage need on upstream lazygit issues (read-only public API).

Usage:
    python3 scripts/metrics/measure_need.py [--out evals/need]

Pulls issues created in [START, END) and all issue comments since START,
saves the raw JSON, and prints/saves summary metrics. Uses GITHUB_TOKEN or
`gh auth token` when available (60 req/h unauthenticated otherwise).
"""
import argparse
import json
import math
import os
import statistics
import subprocess
import sys
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = "jesseduffield/lazygit"
START = "2026-04-01T00:00:00Z"
END = "2026-10-01T00:00:00Z"  # exclusive: covers up to 2026-09-30
MAINTAINER_ROLES = {"OWNER", "MEMBER", "COLLABORATOR"}


def get_token():
    """Return a GitHub token from the env or gh CLI, or None."""
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    try:
        out = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, encoding="utf-8", check=True)
        return out.stdout.strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def fetch_all(path, token):
    """GET every page of a list endpoint (follows `per_page=100&page=N`)."""
    items, page = [], 1
    while True:
        sep = "&" if "?" in path else "?"
        url = f"https://api.github.com/repos/{REPO}/{path}{sep}per_page=100&page={page}"
        req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        with urllib.request.urlopen(req) as resp:
            batch = json.load(resp)
        if not batch:
            return items
        items.extend(batch)
        page += 1


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def is_bot(user):
    return user.get("type") == "Bot" or user.get("login", "").endswith("[bot]")


def percentile(values, pct):
    """Nearest-rank percentile: the ceil(pct% * n)-th smallest value (1-based)."""
    ordered = sorted(values)
    rank = max(1, math.ceil(pct / 100 * len(ordered)))
    return ordered[rank - 1]


def compute_metrics(issues, comments):
    """Pure function: raw API lists -> metrics dict. Tested in tests/."""
    in_window = [
        i for i in issues
        if "pull_request" not in i and START <= i["created_at"] < END
    ]
    external = [i for i in in_window if i["author_association"] not in MAINTAINER_ROLES]

    # First maintainer (non-bot) comment per issue number.
    first_reply = {}
    for c in comments:
        if c["author_association"] not in MAINTAINER_ROLES or is_bot(c["user"]):
            continue
        number = int(c["issue_url"].rsplit("/", 1)[1])
        if number not in first_reply or c["created_at"] < first_reply[number]:
            first_reply[number] = c["created_at"]

    hours = []
    never = 0
    for i in external:
        reply = first_reply.get(i["number"])
        if reply is None:
            never += 1
        else:
            hours.append((parse_time(reply) - parse_time(i["created_at"])).total_seconds() / 3600)

    labels = Counter(l["name"] for i in in_window for l in i["labels"])
    return {
        "window": [START, END],
        "issues": len(in_window),
        "external": len(external),
        "external_never_maintainer_comment": never,
        "external_never_pct": round(100 * never / len(external), 1) if external else 0,
        "first_reply_hours_median": round(statistics.median(hours), 1) if hours else None,
        "first_reply_hours_p90": round(percentile(hours, 90), 1) if hours else None,
        "still_open": sum(1 for i in in_window if i["state"] == "open"),
        "label_counts": dict(labels.most_common()),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="evals/need")
    parser.add_argument("--offline", action="store_true",
                        help="recompute from the raw JSON already saved in --out")
    args = parser.parse_args(argv)

    out = Path(args.out)
    if args.offline:
        issues = json.loads((out / "issues.json").read_text())
        comments = json.loads((out / "comments.json").read_text())
        pulled_at = json.loads((out / "metrics.json").read_text())["pulled_at"]
    else:
        token = get_token()
        issues = fetch_all(f"issues?state=all&since={START}", token)
        comments = fetch_all(f"issues/comments?since={START}", token)
        pulled_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        out.mkdir(parents=True, exist_ok=True)
        (out / "issues.json").write_text(json.dumps(issues, indent=1))
        (out / "comments.json").write_text(json.dumps(comments, indent=1))

    metrics = compute_metrics(issues, comments)
    metrics["pulled_at"] = pulled_at
    text = json.dumps(metrics, indent=2)
    (out / "metrics.json").write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
