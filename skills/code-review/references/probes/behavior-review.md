# probe: behavior-review (behavioral correctness)

**required: true** | **requires: []**

Check behavioral defects introduced or triggered by this change. The review scope and source version follow "Determine the review scope" in `SKILL.md`;
it does not depend on rule packs and is not limited by the language extensions scanned for rules.
Trace actual call chains as needed, unconstrained by the single-level fan-in of `impact-analysis`; not finding a caller does not by itself prove the internal logic correct or incorrect.

## 1. Evidence-gathering method

List the changed behavior entry points or branches from the diff (locations and branches, without presuming defects), and organize them into behavior chains by related state or objects. Complete the evidence gathering and judgment below for each chain in turn. Reason through connected branches together and reuse evidence already read; assess different trigger conditions and consequences separately. After finding an issue, continue checking the other changed paths, even when they share a function or root cause with an existing finding.

1. First read the relevant project entry points and implementations to identify the full signatures actually called, existing contracts, and this change; same-name overloads or similar interfaces cannot substitute.
2. For state changes, locate the relevant direct reads, writes, and wrapper methods (including callbacks) for state fields affected by this change. Connect "state write → guard check → subsequent action", then compare trigger conditions and side effects before and after the change. A getter having no callers or a related implementation being unchanged does not replace checking this chain.
3. Read additional methods, contracts, or tests along the actual call chain only for specific evidence gaps in the current chain that could change the judgment; state the question before reading more. For library or framework calls that decide the conclusion, verify the target version's interface declaration, method contract, or implementation; do not infer return values and exceptions from method names. When model or cache reads are involved, follow the object acquisition, creation, and wrapping paths to verify the actual returned implementation and relevant overridden methods; do not infer behavior from interface fields, method names, or default implementations alone.
4. Once this chain has a judgment of "confirmed issue", "ruled out with evidence", or "unverified with a specific gap", move to the next chain. State the basis for exclusions; do not treat an unverified item as ruled out. Revisit a judged chain only when new evidence or a concrete counterexample could change the conclusion, reusing existing evidence.

Expected behavior may be based on interface contracts, design, existing tests, or explicit code invariants; do not invent business rules.

## 2. Behavioral checks

For the main paths affected by this change, check with the entry points, callers, and context in mind:

- Do conditional branches behave as expected, and are there inverted or missing branches? When routing changes, compare the actual paths for the same input before and after the change, and include pre-existing defects triggered by the new path in this round's checks.
- Are state transitions allowed, and do side effects run under the correct conditions?
- Are nulls, empty collections, and numeric boundaries handled correctly?
- After an exception or partial failure, are state and resources handled correctly?

Choose applicable check directions and concrete counterexamples for each behavior chain, and reason through them:

- **Parsing / validation**: first confirm the input language and dependency versions, and proactively read the corresponding syntax or format contract; the current sample alone cannot stand for valid input. Choose valid equivalent forms per the contract, and check consistency along "parse → validate → use" and whether validation can be bypassed.
- **Serialization / template rendering**: follow the call chain to read the actual wrapping, rendering, and parsing implementations, and compare with the related old entry points. Trace variable values along the actual conversion order, choose inputs such as quotes, backslashes, or newlines, and check whether escaping or decoding changes the original value or breaks the structure.

**Concurrency and async check matrix**: when shared state, retries, or async tasks are involved, select applicable rows from the code signals in this change; a behavior chain may match multiple rows.

| Type and code signal | Interleaving or ordering to examine | Guarantee to verify before ruling the issue out |
| --- | --- | --- |
| Check-then-act: inspect a cache, state, or existence before acting | Another actor changes state between the check and action, and the original actor acts on the stale result; this includes access without locks and operations spanning separate critical sections | Check and act or recheck within one critical section, or use an equivalent atomic protocol; individually locked reads and writes do not establish compound atomicity |
| Read-modify-write: read an old value, compute, then write back | Two actors read the same old value; the later write overwrites the earlier update | A lock, atomic operation, or transaction with the required isolation semantics protects the entire operation |
| Visibility and publication: initialize objects or update readiness flags across threads | A reader observes readiness but not complete or current data | Effective publication and visibility guarantees connect the actual reads and writes, or the state is confined to one thread |
| Cancellation and task termination: completion, exception, or cancellation callbacks release busy/loading | The state is released while the original task and subtasks still run, allowing a new task to enter | Separately verify completion, exception, and cancellation cleanup ordering, re-entry guards, and task isolation against the project contract; cancellation notification is not task termination |
| Stale callbacks: old and new tasks share state or results | A late completion, exception, or cancellation callback from an old task overwrites or clears new task state | Callbacks verify task identity or version, or actual ordering and isolation guarantees prevent the effect |
| Repeated execution: retries, duplicate messages, or repeated triggers cause side effects | Two executions pass the check and repeat an operation required to happen only once | Atomic claims, deduplication, or idempotency meet the business contract; idempotency must cover state writes and externally observable side effects, and identical computed results alone do not rule out an issue; repetition permitted by the project contract alone is not a finding |
| Deadlock: multiple locks, or calls to other components or callbacks while holding a lock | Different paths acquire locks in reverse order or wait for each other to finish | Consistent lock ordering, avoiding waits while holding locks, or another actual guarantee prevents the wait cycle |

For applicable rows, locate the actual thread, task, or callback entry points and relevant reads, writes, and locks. For operation races, give a concrete interleaving with state changes; for visibility and publication issues, explain the relevant reads and writes and their synchronization and publication guarantees. Exclusions must identify a guarantee that prevents that order or its consequence, not merely say "locked" or "mutually exclusive branches". Record specific evidence gaps under section 1 rather than treating them as exclusions. Do not enumerate every thread combination, force findings, or output the entire matrix; reuse existing evidence and the "actual check scope".

For other behavioral changes, choose counterexamples per the main paths.

## 3. Recording and reporting

Check records uniformly state:
**handling point location → trigger conditions and specific input → expected behavior and basis → relevant code path → actual behavior and consequence**.

Once the main paths have these judgments, reuse the records to assemble and write the probe JSON. Do not routinely expand dependencies or recheck judged paths while finishing. If new evidence, a concrete counterexample, or contradictory evidence could change a conclusion, return to the relevant chain for evidence gathering.
In the return message, use the existing "actual check scope" to briefly state, per path, what was checked, what remains unverified, and the specific gaps, then finish; do not add fields or report sections.

Confirmed issues go into the finding's `evidence`; grading and contract-conflict handling follow the [output contract](../output-schema.md).
Record different root causes or consequences separately; do not merge them to evade grading. Issues that depend on unresolved contract conflicts must be listed separately as unverified items even when no finding is created.
When the syntax basis, the actual implementation path, or the reachability of a valid triggering input has not been verified, state the specific gap and do not treat it as a proven defect.
Checks not completed or with insufficient evidence are listed as unverified items and limitations, not lumped into "checked"; when not run, mark "static reasoning" and do not call it reproduced.

Behavioral findings do not require an existing rule ID and are not subject to `repo-guard`'s HIGH-only reporting limit.
