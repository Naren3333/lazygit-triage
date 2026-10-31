import precheck
from validate_labels import load_labels

CATALOG = load_labels()
MARKER = "<!-- replay upstream=#{n} created_at=2026-05-01T00:00:00Z author_association={a} -->"


def issue(assoc="NONE", body="text", labels=(), login="someone", type_="User"):
    return {"author_association": assoc, "body": body,
            "labels": [{"name": n} for n in labels],
            "user": {"login": login, "type": type_}}


def decide(i, replay=False, used=0, cap=40):
    return precheck.decide(i, replay, used, cap, CATALOG)


def test_external_issue_proceeds():
    assert decide(issue()) == (True, "ok")


def test_template_type_label_does_not_count_as_triaged():
    assert decide(issue(labels=["bug"]))[0] is True


def test_live_maintainer_skipped():
    assert decide(issue(assoc="MEMBER")) == (False, "author is MEMBER")


def test_replay_owner_with_external_marker_proceeds():
    # The bug this design fixes: sandbox owner opens every replayed case.
    body = "x\n" + MARKER.format(n=5542, a="NONE")
    assert decide(issue(assoc="OWNER", body=body), replay=True)[0] is True


def test_replay_maintainer_case_skipped_g12():
    body = "help test\n" + MARKER.format(n=5974, a="MEMBER")
    assert decide(issue(assoc="OWNER", body=body), replay=True) == (False, "author is MEMBER")


def test_marker_ignored_outside_replay():
    body = "x\n" + MARKER.format(n=1, a="NONE")
    assert decide(issue(assoc="OWNER", body=body), replay=False)[0] is False


def test_bot_skipped():
    assert decide(issue(login="dependabot[bot]", type_="Bot")) == (False, "author is a bot")


def test_already_triaged_skipped():
    triage, reason = decide(issue(labels=["bug", "needs-info"]))
    assert triage is False and "already triaged" in reason


def test_daily_cap_boundary():
    assert decide(issue(), used=1, cap=2)[0] is True
    assert decide(issue(), used=2, cap=2) == (False, "daily cap reached (2/2)")


def test_main_writes_github_output(tmp_path, monkeypatch, capsys):
    out = tmp_path / "out"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    monkeypatch.setenv("GITHUB_RUN_ID", "7")
    responses = {
        "repos/o/r/issues/5": issue(),
        "runs": {"workflow_runs": [{"id": 7}, {"id": 6}]},  # 7 = this run
    }
    monkeypatch.setattr(precheck, "gh_api",
                        lambda p: responses["runs" if "/runs" in p else p])
    assert precheck.main(["--issue", "5", "--repo", "o/r", "--cap", "1"]) == 0
    assert out.read_text() == "triage=false\nreason=daily cap reached (1/1)\n"
