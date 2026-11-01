# Code Review · {Requirement title}

> slug: `{YYYY-MM-DD-kebab-case-topic}`
> PR: `{PR link}`

## 1. Test Quality and Coverage

Static test quality: checked scope ____; conclusion and findings ____.

| Metric | Target | Status | Actual | Conclusion |
|---|---|---|---|---|
| Line coverage (incremental) | 85% | Measured / Not measured / Not applicable | ____ | ____ |
| Branch coverage | 80% | Measured / Not measured / Not applicable | ____ | ____ |
| Skipped or weakened related tests | Verify reasons and substitute verification | Checked / Unverified | ____ | ____ |

Reasons for not measured / not applicable / unverified: ____.

## 2. Security & Performance

Checked scope: ____; conclusion: ____; related findings / evidence: ____.

## 3. Lessons write-up list (if a lessons directory exists)

Files written and lesson summary: ____ (write "None" when there is nothing to record).

## 4. Acceptance criteria check-off (vs acceptance criteria, if any)

- [ ] Acceptance 1:
- [ ] Acceptance 2:
- [ ] Acceptance 3:

## 5. Probe Results

Review mode: `worktree` / `commits`, `base=______` (commit ID)

Review target: working tree / `head=______` (commit ID)

Changed-file list and diff: ______ (`worktree` must include untracked added files; for evidence-gathering see step 1 of `SKILL.md`)

Checked scope and additional notes: ____.

<!-- code-review:probes:start -->
Filled in by the script with the probe summary and issue details.
<!-- code-review:probes:end -->

> Anything not covered / not verified due to skips, execution failures, or insufficient evidence must be noted in section 6; do not write unchecked items as passed.

## 6. Conclusion

<!-- code-review:gate:start -->
Filled in by the script with recorded issues and probe blocking statuses.
<!-- code-review:gate:end -->

**Content not covered or verified, and why**: ____ (write "None" if none)

Test status: passed / failed / not run / unverified; evidence: ____.
CI status: passed / failed / not run / unverified; evidence: ____.

Conclusion notes and follow-up suggestions: ____ (respect the HARD-GATE; must not overturn the blocking facts recorded above).

A passing static review does not mean tests, CI, or other merge conditions are met.
