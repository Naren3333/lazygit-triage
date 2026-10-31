import replay_marker as rm

BODY = ("Keys broken in Konsole\n"
        "<!-- replay upstream=#5542 created_at=2026-04-10T08:00:00Z "
        "author_association=NONE -->")


def test_parse():
    assert rm.parse(BODY) == {"upstream": 5542, "created_at": "2026-04-10T08:00:00Z",
                              "author_association": "NONE"}
    assert rm.parse("no marker") is None
    assert rm.parse(None) is None


def test_replay_mode_uses_marker_not_live_owner():
    # The sandbox owner opened the issue, but upstream author was external.
    assert rm.effective_association("OWNER", BODY, replay_mode=True) == "NONE"


def test_live_mode_ignores_marker():
    assert rm.effective_association("NONE", BODY.replace("NONE", "OWNER"),
                                    replay_mode=False) == "NONE"


def test_marker_maintainer_role_honoured_in_replay():
    body = BODY.replace("author_association=NONE", "author_association=MEMBER")
    assert rm.effective_association("OWNER", body, replay_mode=True) == "MEMBER"


def test_marker_without_role_or_garbage_role_is_external():
    no_role = "<!-- replay upstream=#1 created_at=2026-04-10T08:00:00Z -->"
    assert rm.effective_association("OWNER", no_role, replay_mode=True) == "NONE"
    garbage = no_role.replace("-->", "author_association=ADMIN -->")
    assert rm.effective_association("OWNER", garbage, replay_mode=True) == "NONE"


def test_created_at_cutoff():
    assert rm.effective_created_at("2026-11-01T00:00:00Z", BODY, True) == "2026-04-10T08:00:00Z"
    assert rm.effective_created_at("2026-11-01T00:00:00Z", BODY, False) == "2026-11-01T00:00:00Z"
