# probe: behavior-review (behavioral correctness)

**required: true** | **requires: []**

Check behavioral defects introduced or triggered by this change. The review scope and source version follow "Determine the review scope" in `SKILL.md`;
it does not depend on rule packs and is not limited by the language extensions scanned for rules.
Trace actual call chains as needed, unconstrained by the single-level fan-in of `impact-analysis`; not finding a caller does not by itself prove the internal logic correct or incorrect.

## 1. Evidence-gathering method

Start by locating behavioral changes from the diff, and check the main paths per section 2. When more reading is needed, first state the specific question to verify, then read the directly relevant methods, contracts, or tests:

1. Locate the full signature of the method actually called, and read the corresponding interface declaration and that method's own contract; same-name overloads or similar interfaces cannot substitute.
2. Read the relevant implementation along the actual call chain. For library or framework calls that decide the conclusion, verify the contract or implementation of the target version, and do not infer return values and exceptions from method names. When model or cache reads are involved, follow the object acquisition, creation, and wrapping paths to verify the actual returned implementation and the relevant overridden methods; do not infer behavior from interface fields, method names, or default implementations alone.

Expected behavior may be based on interface contracts, design, existing tests, or explicit code invariants; do not invent business rules.
Once the evidence is sufficient to confirm or rule out the suspicion, stop tracing that path; continue only when a specific evidence gap could change the judgment.

## 2. Behavioral checks

For the main paths affected by this change, check with the entry points, callers, and context in mind:

- Do conditional branches behave as expected, and are there inverted or missing branches? When routing changes, compare the actual paths for the same input before and after the change, and include pre-existing defects triggered by the new path in this round's checks.
- Are state transitions allowed, and do side effects run under the correct conditions?
- Are nulls, empty collections, and numeric boundaries handled correctly?
- After an exception or partial failure, are state and resources handled correctly?

For major behavioral changes, first locate the relevant handling points from the diff, then choose specific counterexamples from the following check directions and reason through them:

- **Parsing / validation**: first confirm the input language and dependency versions, and proactively read the corresponding syntax or format contract; the current sample alone cannot stand for valid input. Choose valid equivalent forms per the contract, and check consistency along "parse → validate → use" and whether validation can be bypassed.
- **Serialization / template rendering**: follow the call chain to read the actual wrapping, rendering, and parsing implementations, and compare with the related old entry points. Trace variable values along the actual conversion order, choose inputs such as quotes, backslashes, or newlines, and check whether escaping or decoding changes the original value or breaks the structure.
- **Concurrency and repeated execution**: check reads, writes, and publication of shared state, the atomicity of check-then-act or read-modify-write, and whether retries or async completion order violate business constraints. For suspected issues, confirm the actual sharing scope and concurrent execution paths, verify existing synchronization, transaction, or idempotency guarantees, and give an execution order that causes the error; when visibility is involved, explain the synchronization relationship. For async tasks, separately trace the completion, exception, and cancellation wind-down paths, distinguishing cancellation notification from the task actually ending; when checking whether loading/busy is cleared or re-entry is allowed, check whether the still-running original task and its subtasks can violate business constraints.

For other behavioral changes, choose counterexamples per the main paths.

## 3. Recording and reporting

Check records uniformly state:
**handling point location → trigger conditions and specific input → expected behavior and basis → relevant code path → actual behavior and consequence**.

Confirmed issues go into the finding's `evidence`; grading and reporting follow the [output contract](../output-schema.md).
Before grading, verify the basis per "Handling contract conflicts" in the output contract, and list both sides when a conflict exists. Do not default to "tests win" based merely on an old implementation or comment. If the judgment depends on an unresolved conflict, list it as an unverified item; if kept as a finding, note "contract to be confirmed" in the summary and cap severity at `medium`. Other issues with independent, sufficient evidence are graded as usual.
Create separate items for different root causes or different consequences, and do not merge issues that depend on an unresolved conflict into the evidence of an independent high finding to evade grading; even if no finding is created, they must be listed separately among the report's unverified items.
When the syntax basis, the actual implementation path, or the reachability of a valid triggering input has not been verified, state the specific gap and do not treat it as a proven defect.
Checks not completed or with insufficient evidence are listed as unverified items and limitations, not lumped into "checked"; when not run, mark "static reasoning" and do not call it reproduced.

Behavioral findings do not require an existing rule ID and are not subject to `repo-guard`'s HIGH-only reporting limit.
