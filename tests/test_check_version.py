import json

import check_version as cv

RELEASES = [
    {"tag_name": "v0.52.0", "published_at": "2025-06-01T00:00:00Z"},
    {"tag_name": "v0.55.1", "published_at": "2026-02-01T00:00:00Z"},
    {"tag_name": "v0.56.0", "published_at": "2026-05-01T00:00:00Z"},
    {"tag_name": "v0.60.0", "published_at": "2026-12-01T00:00:00Z"},  # future
]


def test_parse_lazygit_version_output_preferred():
    text = ("Ubuntu 24.04, git 2.43\n"
            "commit=abc, build date=..., version=0.55.1, os=linux")
    assert cv.parse_version(text) == (0, 55, 1)


def test_parse_skips_non_lazygit_numbers():
    assert cv.parse_version("Ubuntu 24.04 git 2.43 lazygit v0.32.2") == (0, 32, 2)
    assert cv.parse_version("Windows 11, no version given") is None


def test_future_releases_ignored():
    assert cv.latest_as_of(RELEASES, "2026-06-01T00:00:00Z") == (0, 56, 0)
    assert cv.latest_as_of(RELEASES, "2026-03-01T00:00:00Z") == (0, 55, 1)


def test_ancient_version_too_old():
    result = cv.check("lazygit v0.32.2", RELEASES, "2026-06-01T00:00:00Z")
    assert result == {"found": "v0.32.2", "latest": "v0.56.0",
                      "minors_behind": 24, "too_old": True}


def test_boundary_three_behind_is_ok():
    assert cv.check("v0.53.0", RELEASES, "2026-06-01T00:00:00Z")["too_old"] is False
    assert cv.check("v0.52.0", RELEASES, "2026-06-01T00:00:00Z")["too_old"] is True


def test_no_version_found():
    result = cv.check("it crashes", RELEASES, "2026-06-01T00:00:00Z")
    assert result["found"] is None and result["too_old"] is False


def test_cli(tmp_path, capsys):
    path = tmp_path / "r.json"
    path.write_text(json.dumps(RELEASES))
    assert cv.main(["--text", "v0.32.2", "--as-of", "2026-06-01T00:00:00Z",
                    "--releases", str(path)]) == 0
    assert json.loads(capsys.readouterr().out)["too_old"] is True
