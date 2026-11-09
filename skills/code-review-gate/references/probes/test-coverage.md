# probe: test-coverage (test quality and incremental coverage)

**required: true** | **requires: []**

Read [`common.md`](common.md) first; it defines the constraints shared by all probes.

Each round, the AI checks the quality of the relevant tests; coverage is an optional sub-item.
Tests need not be run, nor coverage measured, every round.

## 1. Inputs and boundaries

- Locate the relevant test source and configuration for the target version per "Determine the review scope" in `SKILL.md`.
- Coverage reports and measurement commands are both optional.

First confirm whether the available material is a complete project or only a diff / partial source / minimal snapshot.
With only partial material, you can only say "no relevant tests found in the current material"; the missing part is recorded as unverified, and you must not assert that the original project has no tests.

## 2. Test quality checks (every round)

First compare against expected behavior to distinguish implementation regressions from problems in the tests themselves. When existing tests correctly reveal this regression, record their coverage and hand the behavioral suspicion and evidence back to the main executor; do not conclude that the tests are defective merely because they were not modified.

Using the relevant tests and the code under test, check the tests themselves:

- **Assertions**: do they verify real results and distinguish a correct implementation from the relevant errors, rather than merely executing code or unconditionally asserting `true`? For key changes, choose a plausible incorrect behavior (such as a wrong return value, an incorrect boundary condition, or a missing state update) and identify the specific test and assertion that would detect it. If none is found, assess whether the tests actually inspected have a scenario or assertion gap. Against expected behavior, check whether mocks bypass the logic under test, exceptions are swallowed, and important side effects such as state changes or call counts are verified; using mocks alone does not make a test ineffective.
- **Scenarios**: do they cover the important boundaries and failure paths of this change; check retries and concurrency according to actual applicability.
- **Stability**: do they depend on execution order, unstable time, or an uncontrollable external environment?
- **Test changes**: were relevant tests deleted, skipped, commented out, or weakened? Judge with the reason and any substitute verification whether valid checks were lost; do not mark it high based merely on a deletion or a skip / pending marker.

These checks are static judgments: do not modify the implementation or automatically run mutation testing, and do not present them as executed verification. Meeting coverage targets does not establish test effectiveness.

Produce findings only for proven defects in the tests themselves or for scenario / assertion gaps, stating the location, expected-behavior basis, and risk; describe the gap within the actually checked test scope.
When expected behavior is still under contract dispute, record an unverified item and do not presuppose assertion outcomes. Grade per `references/output-schema.md`; a missing test is not automatically high.

## 3. Optional coverage check and reporting

Use effective `line_target` / `branch_target` handed off by init; project policy takes precedence, defaults are 85 / 80.
Compare against these effective targets, not a separate fixed 85% baseline.

1. Prefer reusing an existing coverage report that corresponds to the review's target version and modules.
2. When no corresponding report exists, run measurement only if the project already has a measurement method and this round's task allows it; otherwise record "not measured" and still complete the test quality check.
3. With a valid report, compute the executable-line coverage of production source lines added or modified by this diff:
   `diff line coverage = covered executable changed lines / total executable changed lines × 100%`.
   The report must state the numerator, denominator, and result; do not use whole-file coverage; when processing JaCoCo XML, read the details at the end.

| Coverage situation | Record and handling |
|---|---|
| Measured diff line coverage ≥ line_target | Meets target |
| Measured diff line coverage < line_target | high finding, blocks merge |
| Branch coverage | Target branch_target (default 80%); falling short is advisory only and does not block or lower scores |
| Confirmed no executable incremental lines | Record coverage as "not applicable", explain why, and do not fill in 0% or 100% |
| A specified report is unreadable, unparsable, incomplete, or version-mismatched, or the measurement command fails | `error`; must not be recorded as "not measured" or "not applicable" |

Return the report path, target version, numerator/denominator, and percentage for valid coverage; the main executor reports them per `SKILL.md`. Do not fill unmeasured or inapplicable metrics with 0.

## 4. Reporting

Record test quality, coverage status, and unverified items separately.
`passed` does not mean the tests were run or coverage was measured.

## 5. JaCoCo incremental line calculation (read when processing XML)

First confirm that the report corresponds to this target version, completely includes the mapped production source sets, and has line debug information. Once confirmed, use the read-only calculator:

```bash
"${CODE_REVIEW_PYTHON:-python}" -X utf8 "$CODE_REVIEW_SKILL_DIR/scripts/coverage-diff.py" \
  --project-root . --base {base} --head {head} \
  --jacoco module/src/main/java module/target/site/jacoco/jacoco.xml \
  --confirm-report-scope
```

- **Inputs**. For uncommitted changes, replace `--head {head}` with `--worktree`. Repeat `--jacoco SOURCE_ROOT XML` for multiple production roots, using non-overlapping project-relative POSIX paths and a separate report per root. `--confirm-report-scope` declares that the report conditions above have been checked; the script cannot establish them.
- **Output**. Read JSON fields `status`, `covered_lines`, `executable_lines` and `percent`, then assess and hand off per section 3. `not_applicable` means no executable incremental lines; record failures as `error` per section 3. Compare thresholds using integer numerator and denominator. `percent` is a decimal string and cannot be passed directly to the integer-only `coverage --line`.
- **Handoff**. Put calculation results in the relevant finding's `evidence` and the return message. Probe JSON follows `references/output-schema.md`; do not add a top-level `coverage` field or embed the entire calculation result.
