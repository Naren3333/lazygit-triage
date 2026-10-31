import json

import pytest

import validate_labels as v

CATALOG = v.load_labels()


@pytest.mark.parametrize("labels", [
    ["bug"],
    ["bug", "windows", "credentials", "needs-info"],
    ["question", "installation"],
    ["needs-triage"],                    # unsure/junk escape hatch
    ["bug", "needs-triage"],
])
def test_valid(labels):
    assert v.validate(labels, CATALOG) == []


@pytest.mark.parametrize("labels, fragment", [
    (["bug", "blocks-release"], "unknown"),
    (["bug", "bug"], "duplicate"),
    (["bug", "windows", "UI", "needs-info", "possible-duplicate"], "too many labels"),
    (["windows"], "exactly 1 type"),
    (["bug", "enhancement"], "exactly 1 type"),
    (["bug", "windows", "UI", "i18n"], "too many area"),
    ([], "exactly 1 type"),
])
def test_invalid(labels, fragment):
    errors = v.validate(labels, CATALOG)
    assert any(fragment in e for e in errors), errors


def test_every_label_has_required_fields():
    for name, d in CATALOG["labels"].items():
        assert d["kind"] in {"type", "area", "status"}, name
        for key in ("definition", "positive", "negative", "color"):
            assert d[key], (name, key)


def test_cli_exit_codes(tmp_path, capsys):
    good = tmp_path / "good.json"
    good.write_text(json.dumps({"labels": ["bug"]}))
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"labels": ["close-all"]}))
    assert v.main([str(good)]) == 0
    assert v.main([str(bad)]) == 1
    assert "unknown" in capsys.readouterr().out
