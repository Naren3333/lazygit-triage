import json

import prepare_context as pc

ISSUE = {"number": 3, "title": "t", "body": "b\n<!-- replay upstream=#5542 created_at=2026-04-10T08:00:00Z "
         "author_association=NONE -->", "labels": [{"name": "bug"}], "created_at": "2026-11-01T00:00:00Z",
         "user": {"login": "owner"}, "author_association": "OWNER"}


def test_issue_context_replay_cutoff_from_marker():
    ctx = pc.issue_context(ISSUE, replay=True)
    assert ctx["cutoff"] == "2026-04-10T08:00:00Z"
    assert ctx["labels"] == ["bug"]
    # Only data the agent needs: no author identity or association.
    assert set(ctx) == {"number", "title", "body", "labels", "cutoff"}


def test_issue_context_live_cutoff_is_created_at():
    assert pc.issue_context(ISSUE, replay=False)["cutoff"] == "2026-11-01T00:00:00Z"


def test_main_replay_copies_frozen_context(tmp_path, monkeypatch):
    ctx_dir = tmp_path / "ctx"
    ctx_dir.mkdir()
    (ctx_dir / "issue-index.json").write_text("[]")
    (ctx_dir / "releases.json").write_text("[]")
    monkeypatch.setattr(pc, "GOLDEN_CONTEXT", ctx_dir)
    monkeypatch.setattr(pc, "gh_api", lambda path, paginate=False: ISSUE)
    out = tmp_path / "out"
    assert pc.main(["--issue", "3", "--repo", "o/r", "--replay", "--out", str(out)]) == 0
    assert json.loads((out / "issue.json").read_text())["cutoff"] == "2026-04-10T08:00:00Z"
    assert (out / "releases.json").read_text() == "[]"
