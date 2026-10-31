# Upstream snapshot

The lazygit source in this repo is a `git archive` of
`jesseduffield/lazygit` at commit `eb351dcdeb108825f63516453b51566a4a40b1a9`
(2026-03-31T13:57:17+02:00, "README.md: Update Sponsors (#5397)"): the last
first-parent commit on `master` before 2026-04-01T00:00:00Z.

Found with:

    git log master --first-parent --before='2026-04-01T00:00:00Z' -1

Note: `git rev-list -1 --before=2026-04-01 master` (as originally planned)
returned 4c2c0ce (2026-04-01T09:27Z) because `--before` without a timezone
uses local time and rev-list does not walk first-parent order, so it was
rejected.

Removed from the snapshot so nothing upstream runs in this sandbox:
`.github/workflows/*` (ci, release, close-issues, codespell, sponsors,
check-required-label), `.github/dependabot.yml`, `.github/FUNDING.yml`.
`test/.gitconfig` was a symlink to `global_git_config`; it is a copy here
because Windows tar could not create the symlink.
