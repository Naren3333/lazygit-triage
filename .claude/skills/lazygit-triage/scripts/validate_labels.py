#!/usr/bin/env python3
"""Validate a triage proposal against labels.json before anything is emitted.

Usage:
    python3 validate_labels.py proposal.json [--labels path/to/labels.json]

proposal.json: {"labels": ["bug", "windows"], "comment": "..." | null}

Exit 0 and print "OK" when valid; exit 1 and print one reason per line otherwise.
Rules (from labels.json "limits"): every label is defined, no repeats,
<= max_total labels, exactly one type label (unless the only label is
needs-triage, which is the "unsure/junk" escape), <= area_max area labels.
"""
import argparse
import json
import sys
from pathlib import Path

DEFAULT_LABELS = Path(__file__).resolve().parent.parent / "labels.json"


def load_labels(path=DEFAULT_LABELS):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate(proposed, catalog):
    """Return a list of error strings; empty list means valid."""
    defs, limits = catalog["labels"], catalog["limits"]
    errors = []

    unknown = [l for l in proposed if l not in defs]
    if unknown:
        errors.append(f"unknown labels: {unknown}")
    if len(set(proposed)) != len(proposed):
        errors.append("duplicate labels")
    if len(proposed) > limits["max_total"]:
        errors.append(f"too many labels: {len(proposed)} > {limits['max_total']}")

    kinds = [defs[l]["kind"] for l in proposed if l in defs]
    types = kinds.count("type")
    only_needs_triage = list(proposed) == ["needs-triage"]
    if types != limits["type_exactly"] and not only_needs_triage:
        errors.append(f"need exactly {limits['type_exactly']} type label, got {types}")
    if kinds.count("area") > limits["area_max"]:
        errors.append(f"too many area labels: {kinds.count('area')} > {limits['area_max']}")
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("proposal")
    parser.add_argument("--labels", default=DEFAULT_LABELS)
    args = parser.parse_args(argv)

    proposal = json.loads(Path(args.proposal).read_text(encoding="utf-8"))
    errors = validate(proposal.get("labels", []), load_labels(args.labels))
    if errors:
        print("\n".join(errors))
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
