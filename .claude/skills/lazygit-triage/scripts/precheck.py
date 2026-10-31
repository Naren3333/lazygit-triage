#!/usr/bin/env python3
"""Deterministic gate run BEFORE the agent (gh-aw pre-activation job).

Usage (in the workflow):
    python3 precheck.py --issue N --repo owner/name [--replay] [--cap 40]

Decides whether the model should run at all. Skips when:
  1. the author is a maintainer (OWNER/MEMBER/COLLABORATOR) - in replay
     mode this comes from the replay marker, not the live issue (the
     sandbox owner opens every replayed case);
  2. the author is a bot;
  3. the issue already has an area/status label from labels.json
     (already triaged; type labels don't count, templates add those);
  4. today's (UTC) runs of this workflow already reached the daily cap.

Writes `triage=true|false` and `reason=...` to $GITHUB_OUTPUT (or stdout
when unset). Always exits 0 so a skip is a clean skip, not a failure.
Over-cap issues are not labelled here (this job has read-only rights);
they stay unlabelled and are listed by the `no:label` search or re-run
with workflow_dispatch the next day (see DESIGN.md, Q3).
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

import replay_marker
from validate_labels import load_labels

MAINTAINER_ROLES = {"OWNER", "MEMBER", "COLLABORATOR"}
WORKFLOW_FILE = "issue-triage.lock.yml"


def gh_api(path):
    """GET a GitHub API path with the gh CLI (uses GH_TOKEN). Returns parsed JSON."""
    out = subprocess.run(["gh", "api", path], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def runs_today(repo, today, current_run_id=None):
    """Runs of the triage workflow created today (UTC), excluding this one.

    Conservative: skipped runs count too, so the cap can only bite earlier.
    """
    data = gh_api(f"repos/{repo}/actions/workflows/{WORKFLOW_FILE}/runs"
                  f"?created=%3E%3D{today}&per_page=100")
    return sum(1 for r in data.get("workflow_runs", [])
               if str(r["id"]) != str(current_run_id))


def decide(issue, replay, used_today, cap, catalog):
    """Pure decision. Returns (triage: bool, reason: str)."""
    association = replay_marker.effective_association(
        issue.get("author_association", "NONE"), issue.get("body"), replay)
    if association in MAINTAINER_ROLES:
        return False, f"author is {association}"

    user = issue.get("user") or {}
    if user.get("type") == "Bot" or user.get("login", "").endswith("[bot]"):
        return False, "author is a bot"

    defs = catalog["labels"]
    agent_labels = [l["name"] for l in issue.get("labels", [])
                    if defs.get(l["name"], {}).get("kind") in {"area", "status"}]
    if agent_labels:
        return False, f"already triaged: {agent_labels}"

    if used_today >= cap:
        return False, f"daily cap reached ({used_today}/{cap})"
    return True, "ok"


def write_outputs(triage, reason):
    lines = f"triage={'true' if triage else 'false'}\nreason={reason}\n"
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(lines)
    print(lines, end="")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issue", type=int, required=True)
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"))
    parser.add_argument("--replay", action="store_true",
                        help="golden replay: trust the replay marker for author/date")
    parser.add_argument("--cap", type=int, default=int(os.environ.get("DAILY_CAP") or 40))
    args = parser.parse_args(argv)

    issue = gh_api(f"repos/{args.repo}/issues/{args.issue}")
    today = datetime.now(timezone.utc).date().isoformat()
    used = runs_today(args.repo, today, os.environ.get("GITHUB_RUN_ID"))
    triage, reason = decide(issue, args.replay, used, args.cap, load_labels())
    write_outputs(triage, reason)
    return 0


if __name__ == "__main__":
    sys.exit(main())
