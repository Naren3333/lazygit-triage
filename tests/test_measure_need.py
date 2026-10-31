import measure_need as m


def issue(number, created, assoc="NONE", state="open", labels=(), pr=False):
    item = {"number": number, "created_at": created, "author_association": assoc,
            "state": state, "labels": [{"name": n} for n in labels]}
    if pr:
        item["pull_request"] = {}
    return item


def comment(number, created, assoc="OWNER", login="maint", type_="User"):
    return {"issue_url": f"https://api.github.com/repos/x/y/issues/{number}",
            "created_at": created, "author_association": assoc,
            "user": {"login": login, "type": type_}}


def test_percentile_nearest_rank():
    values = list(range(1, 116))  # 115 values, like the real data
    assert m.percentile(values, 90) == 104  # ceil(0.9 * 115) = 104th
    assert m.percentile([5], 90) == 5


def test_window_excludes_prs_and_out_of_range():
    issues = [
        issue(1, "2026-04-01T00:00:00Z"),          # first instant: in
        issue(2, "2026-10-01T00:00:00Z"),          # end is exclusive: out
        issue(3, "2026-03-31T23:59:59Z"),          # before: out
        issue(4, "2026-05-01T00:00:00Z", pr=True), # PR: out
    ]
    assert m.compute_metrics(issues, [])["issues"] == 1


def test_first_maintainer_reply_ignores_bots_and_externals():
    issues = [issue(1, "2026-05-01T00:00:00Z"), issue(2, "2026-05-01T00:00:00Z")]
    comments = [
        comment(1, "2026-05-01T01:00:00Z", assoc="NONE"),                  # external
        comment(1, "2026-05-01T02:00:00Z", login="x[bot]", type_="Bot"),   # bot
        comment(1, "2026-05-01T05:00:00Z"),                                # later maint
        comment(1, "2026-05-01T03:00:00Z"),                                # first maint
    ]
    result = m.compute_metrics(issues, comments)
    assert result["first_reply_hours_median"] == 3.0
    assert result["external_never_maintainer_comment"] == 1  # issue 2


def test_maintainer_authored_issues_not_external_and_labels_counted():
    issues = [issue(1, "2026-05-01T00:00:00Z", assoc="MEMBER", labels=["bug"]),
              issue(2, "2026-05-01T00:00:00Z", state="closed", labels=["bug"])]
    result = m.compute_metrics(issues, [])
    assert result["external"] == 1
    assert result["still_open"] == 1
    assert result["label_counts"] == {"bug": 2}
