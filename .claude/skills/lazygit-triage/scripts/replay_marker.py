"""Parse the hidden golden-replay marker that replay.py puts in issue bodies.

    <!-- replay upstream=#5542 created_at=2026-04-10T08:00:00Z author_association=NONE -->

Replayed issues are opened by the sandbox owner, so live metadata is wrong
for them: the author is always OWNER and created_at is "now". The marker
carries the upstream values instead.

The marker is only read when replay mode is on, and replay mode is switched
on by the workflow (workflow_dispatch input), never by issue text. Anyone can
still type a marker into an issue, but it can only make the bot do *less*:
  - created_at only narrows the duplicate-search / release cutoff to older data;
  - author_association=OWNER only makes precheck skip that one issue.
"""
import re

MARKER_RE = re.compile(
    r"<!--\s*replay\s+upstream=#(?P<upstream>\d+)"
    r"\s+created_at=(?P<created_at>\S+)"
    r"(?:\s+author_association=(?P<author_association>[A-Z_]+))?\s*-->"
)
KNOWN_ROLES = {"OWNER", "MEMBER", "COLLABORATOR", "CONTRIBUTOR",
               "FIRST_TIMER", "FIRST_TIME_CONTRIBUTOR", "MANNEQUIN", "NONE"}


def parse(body):
    """Return the marker fields as a dict, or None when the body has no marker."""
    match = MARKER_RE.search(body or "")
    if not match:
        return None
    fields = match.groupdict()
    fields["upstream"] = int(fields["upstream"])
    return fields


def effective_association(live_association, body, replay_mode):
    """Author association that precheck should use.

    Replay mode + marker: the marker's role (unknown/missing role -> NONE,
    i.e. treat as external). Otherwise: the live value from the API.
    """
    marker = parse(body) if replay_mode else None
    if marker is None:
        return live_association
    claimed = marker.get("author_association")
    return claimed if claimed in KNOWN_ROLES else "NONE"


def effective_created_at(live_created_at, body, replay_mode):
    """Cutoff date for duplicate search and release lookup."""
    marker = parse(body) if replay_mode else None
    return marker["created_at"] if marker else live_created_at
