# Probe output contract (findings)

This file defines the finding fields, severity levels, handling statuses, and probe execution statuses, for use by probes when they write standalone JSON.
A finding is one specific problem; `severity` indicates how serious it is, a finding's `status` indicates handling progress, and the probe status indicates the execution result of one round of checks.

## 1. How to write a single issue

| Field | Requirement | Value | Description |
|---|---|---|---|
| `id` | Required | `<probe>-<number>` | Globally unique, number starts at 1, **must be stable** |
| `probe` | Required | Probe name | Probe name taken from `references/probes.yaml` |
| `severity` | Required | `high` / `medium` / `low` | See the criteria table below |
| `status` | Required | `open` / `reconciled` / `wontfix` / `false-positive` | See the state machine below |
| `location` | Required | `path:line` | When no line can be located, use the file level and explain why |
| `summary` | Required | One sentence | Say **what the problem is**, not empty phrases like "consider optimizing" |
| `evidence` | Required | Concrete basis | Cite a rule ID / interface contract / code path / test output. **Anything without evidence is not a finding** |
| `repro` | Optional | Verification command | E.g. `grep -n 'formatCents' src/…/Calculator.java`, `git show <head>:<path>`. Read-only evidence commands only; must not build or run tests |
| `reconciled_by` | Conditionally required | Handling note | Fill in when `status=reconciled`: where it was changed and why |
| `reconcile_commit` | Optional | commit id | Fill in when a corresponding handling commit exists |

Optional fields not provided and conditional fields that do not apply may be omitted; empty fields need not be filled.

Each probe saves this round's records as a standalone `probes/<probe-name>.json`. For example:

```json
{
  "probe": "test-coverage",
  "status": "failed",
  "duration": 12,
  "findings": [{
    "id": "test-coverage-1",
    "probe": "test-coverage",
    "severity": "high",
    "status": "open",
    "location": "src/main/java/com/example/Calculator.java:137",
    "summary": "Incremental line coverage is 60%, below the 85% baseline",
    "evidence": "Report matches the target version; 3 of 5 executable changed lines in production code are covered, 3/5 = 60%"
  }]
}
```

`probe`, `status`, and `findings` are required; `duration` is a non-negative integer in seconds and may be omitted, with omission recorded as 0.
`skipped` / `error` must also include a non-empty `reason`; when there are no issues, explicitly write `findings: []` rather than inventing empty records.
Checked scope, limitations, and fix suggestions go in the human report; the machine JSON is the single source of truth, so do not copy full findings or hand-fill counts elsewhere.

## 2. Issue severity

| Level | Criterion | Enters reconciliation |
|---|---|---|
| `high` | Serious security rule violation / money or data correctness issue / HIGH-severity standards rule violation / contract break / measured diff line coverage below the effective project target (default 85%) / acceptance item failing | **Yes** |
| `medium` | Confirmed behavioral defects that deviate from expected behavior, have localized impact, and do not meet the high criteria; maintainability issues, missing tests | No (record only) |
| `low` | Style, naming | No |

Only the three levels above are accepted; other levels are an error and are not auto-converted or used to rewrite historical records.


### Behavioral issues

**1. Verify the basis**

To report `high` on the grounds of violating a method contract, `evidence` must include the full signature of the actual method, the file and line number of the corresponding interface declaration (or the method declaration if there is no interface), and a short excerpt of the contract text. Same-name overloads or similar interfaces cannot substitute.
When there is confirmed to be no textual contract, you may cite specific code invariants or tests and their locations; not having read something cannot be treated as it not existing.
When the basis has not been verified or listed, the maximum is `medium`, noting "contract not verified".

**2. Grade by proven errors**

- `high`: at public contract boundaries such as API / SPI / cache / state machine, an incorrect return, exception, or missed invalidation occurs under reachable inputs. Source-code reasoning may serve as evidence; end-to-end execution is not required.
- Maximum `medium`: the boundary error is not yet proven and downstream impact is only speculated; or the performance issue is unmeasured.

Do not omit a proven behavioral defect solely because performance is unmeasured or downstream effects are unverified.

When a boundary error is proven, unverified downstream UI / templates / integration layers are recorded only in `evidence` and do not lower the severity.

**3. Handling contract conflicts**

When contracts, docs, or tests conflict, list both sides' bases in `evidence`. Only evidence that applies to the target version and explains the conflict can resolve it; "probably a typo / copy-paste / old comment" does not count as evidence.
If the judgment depends on an unresolved conflict, record it as an unverified item; if kept as a finding, the maximum is `medium`, and the summary notes "contract to be confirmed". Other issues with independent, sufficient evidence are graded as usual.
`unverified` is not a finding severity or status.

### Combined risk and test gaps

- **Combined risk**: when multiple distinct issues interact and evidence proves they jointly cause a more serious consequence,
  grade by the combined impact and explain the interaction path.
- **Contract changes and test gaps**: when a corresponding test is confirmed missing, record the test gap; do not automatically escalate it to `high`.
  When evidence already proves that a contract change causes a breaking impact, grade per the severity criteria above.
  When test context is not provided or is incomplete, note "relevant tests unverified", and do not assert that no tests exist on that basis.

## 3. Issue handling statuses

```
open ──┬─→ reconciled      Handled (code changed / tests added)
       ├─→ wontfix         Explicitly not fixing (**must give a reason**, and severity must be medium/low)
       └─→ false-positive  Probe false positive (**must give evidence** explaining why it is not a problem)
```

### Re-running after handling

After a high finding is handled, re-run the corresponding probe and report the result; do not directly hand-edit it to `passed`.
The re-run must state what changed in the code or the basis for judgment; execution status follows the latest result, and historical findings and handling records are retained.

## 4. Probe execution results

`requires` lists the inputs a probe needs, checked against this round's provided materials and default configuration.
Probe execution status is reported separately from the handling status of individual findings:

| Status | Meaning |
|---|---|
| `passed` | The relevant checks completed with no execution errors and no open high findings |
| `failed` | The relevant checks completed with no execution errors but open high findings |
| `skipped` | **Normally skipped per the probe's convention**, e.g. this round did not provide the optional input required by `requires`; the reason must be stated. **Not counted as a failure** |
| `error` | A specified input path does not exist, cannot be read or parsed, or a command / tool failed. Only when `required=true` does it count toward `PROBE_REQUIRED_FAILED`, same as `failed` |

When a specified coverage report path cannot be read, record it as `error`.
Missing or corrupted resources pointed to by the default configuration likewise count as `error` and must not be disguised as a normal skip.
