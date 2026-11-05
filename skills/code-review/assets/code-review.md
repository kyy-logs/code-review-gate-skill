# Code Review · {Requirement title}

> slug: `{YYYY-MM-DD-kebab-case-topic}` · PR: {PR link; omit if none}

## 1. Review Conclusion

<!-- code-review:gate:start -->
Filled in by the script with recorded issues and probe blocking statuses.
<!-- code-review:gate:end -->

| Verification | Status | Evidence |
|---|---|---|
| Tests | Passed / Failed / Not run / Unverified | ____ |
| CI | Passed / Failed / Not run / Unverified | ____ |

Conclusion and next steps: ____ (respect the HARD-GATE and reference relevant finding IDs; do not overturn the blocking facts recorded above).

Key verification limitations: ____ (details in section 3; write "None" if none).

## 2. Findings

<!-- code-review:probes:start -->
Filled in by the script with the probe summary, issue details, and items pending confirmation.
<!-- code-review:probes:end -->

Additional suggestions (if any): reference finding IDs and add only guidance not already included in the finding details; omit when none.

## 3. Review Scope and Limitations

- Review mode: `worktree` / `commits`; `base=______` (commit ID).
- Review target: working tree / `head=______` (commit ID).
- Changed-file list and diff: ______ (`worktree` includes untracked added files; for evidence-gathering see step 1 of `SKILL.md`).
- Actual checked scope: ____ (include applicable behavioral, standards, security, performance, and related test paths).

Content not covered or verified, and why: ____ (write "None" if none; explain skips, execution errors, and evidence gaps; do not write unchecked items as passed).

## 4. Tests and Acceptance

Static test quality: checked scope ____; conclusion and related finding IDs ____ (verify reasons and substitute verification for skipped or weakened related tests).

| Coverage metric | Target | Status | Measured result |
|---|---|---|---|
| Line coverage (incremental) | {line_target}% | Measured / Not measured / Not applicable | ____ |
| Branch coverage | {branch_target}% | Measured / Not measured / Not applicable | ____ |

Measurement basis or reasons for not measured / not applicable: ____.

Acceptance: record "Passed / Failed / Unverified" and evidence against each provided criterion. When none are provided, write "No acceptance criteria provided" without empty checkboxes.

Supporting material (if any): link to existing verification material or Lessons without repeating the report.
