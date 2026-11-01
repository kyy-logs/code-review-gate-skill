# Offline tests

These tests exercise the review pipeline's records, three-level severity
validation, report rendering, and gate behavior. They do not call a model and
do not replace recall evaluation.

Bilingual packaging tests cover shared-script synchronization, report-label
localization, English/Chinese rule extraction, explicit semantic rules, locale
structure checks, and both installable language layouts.

Release-note tests run the NEWS Unreleased generator against temporary Git
histories, including Conventional Commits, keyword fallback, skipped release
subjects, stale blocks, and missing markers. They also exercise the
NEWS-to-README synchronizer, including its Unreleased skip, stale previews,
invalid markers, and repeated runs.

Installation checks cover both the Claude Code and Codex layouts, the unified
installer, repeated installs, existing-config protection, `--dry-run`, and
`--force` backups. They copy into a separate temporary project, including paths
containing spaces. No skill-directory environment override is needed.

Remote-entry checks use a local Git fixture instead of GitHub. They execute the
bootstrap without `__file__`, install a selected tag, cover both hosts and
explicit destinations, preserve conflict/backup behavior and JSON output, and
verify cleanup after successful downloads, missing repositories, and missing
refs. No external network or model calls are made.

Run from the repository root:

```bash
python -m unittest discover -s tests -v
```

Bash-backed gate tests also need a Bash executable:

```bash
CODE_REVIEW_TEST_BASH=/usr/bin/bash python -m unittest discover -s tests -v
```

On Windows with Git Bash, point `CODE_REVIEW_TEST_BASH` at the Git Bash
executable, for example `E:/git/Git/usr/bin/bash.exe`.
