import json

import find_duplicates as fd

INDEX = [
    {"number": 10, "title": "Keybindings broken in Konsole terminal",
     "body": "arrow keys and shift keys do nothing in konsole", "created_at": "2026-04-01T00:00:00Z", "state": "open"},
    {"number": 11, "title": "Crash when opening a bare repository",
     "body": "panic nil pointer bare repo", "created_at": "2026-03-01T00:00:00Z", "state": "open"},
    {"number": 12, "title": "Add option for commit graph colours",
     "body": "feature request colours", "created_at": "2026-03-05T00:00:00Z", "state": "closed"},
    {"number": 13, "title": "Konsole keys do not work",
     "body": "keys broken konsole", "created_at": "2026-06-01T00:00:00Z", "state": "open"},  # future
]


def test_finds_paraphrased_duplicate_first():
    issue = {"number": 99, "title": "Konsole: keys not working",
             "body": "Since update, keys broken inside Konsole"}
    result = fd.rank(issue, INDEX, before="2026-05-01T00:00:00Z", top=3)
    assert result[0]["number"] == 10
    assert result[0]["score"] > result[-1]["score"]


def test_future_issues_excluded_by_cutoff():
    issue = {"number": 99, "title": "Konsole keys broken", "body": ""}
    numbers = [r["number"] for r in fd.rank(issue, INDEX, before="2026-05-01T00:00:00Z", top=10)]
    assert 13 not in numbers


def test_issue_never_matches_itself_and_empty_pool():
    issue = {"number": 10, "title": "x", "body": ""}
    assert all(r["number"] != 10 for r in fd.rank(issue, INDEX, "2027-01-01T00:00:00Z"))
    assert fd.rank(issue, INDEX, before="2000-01-01T00:00:00Z") == []


def test_stopwords_and_tokenize():
    assert fd.tokenize("The lazygit Bug: v0.56.0 crash!") == ["v0.56.0", "crash"]


def test_cli_search(tmp_path, capsys):
    (tmp_path / "issue.json").write_text(json.dumps({"number": 1, "title": "bare repo crash", "body": ""}))
    (tmp_path / "index.json").write_text(json.dumps(INDEX))
    assert fd.main(["--issue-file", str(tmp_path / "issue.json"), "--index", str(tmp_path / "index.json"),
                    "--before", "2026-05-01T00:00:00Z", "--top", "1"]) == 0
    assert json.loads(capsys.readouterr().out)[0]["number"] == 11
