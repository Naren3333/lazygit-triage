# Measured need (upstream lazygit, issues created 2026-04-01 .. 2026-09-30)

Reproduce: `python3 scripts/metrics/measure_need.py` (live, read-only public API)
or `--offline` to recompute `metrics.json` from the saved `issues.json` / `comments.json`.

| metric | value |
|---|---|
| issues in window (PRs excluded) | 181 |
| external authors (not OWNER/MEMBER/COLLABORATOR) | 176 |
| external issues with no maintainer comment | 61 (34.7%) |
| time to first maintainer comment, median | 3.0 h |
| time to first maintainer comment, p90 (nearest rank) | 148.8 h |
| still open at pull time (2026-10-31) | 100 |
| labels used | bug 73, enhancement 72, discussion 6 |

p90 note: 115 external issues got a maintainer reply. Nearest-rank p90 is the
ceil(0.9*115)=104th value = 148.8 h. The preliminary figure of ~103 h was the
103rd value (rank rounded down). The tail is steep (next values 273 h, 446 h).

Limitations: bot comments excluded; "response" = comment only (silent
labels/closes are not counted); bug/enhancement are applied by issue
templates; one 6-month window; selective triage may be maintainer policy,
not neglect; `since=` filters on updated_at, so issues are re-filtered by
created_at locally.
