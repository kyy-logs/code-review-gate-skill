# probe: behavior-review (behavioral correctness)

**required: true** | **requires: []**

Read [`common.md`](common.md) first; it defines the constraints shared by all probes.

Check behavioral defects introduced or triggered by this change. The review scope and source version follow "Determine the review scope" in `SKILL.md`;
it does not depend on rule packs and is not limited by the language extensions scanned for rules.
Trace actual call chains as needed, unconstrained by the single-level fan-in of `impact-analysis`; not finding a caller does not by itself prove the internal logic correct or incorrect.

## 1. Evidence-gathering method

Identify changed behavior entry points or branches from the diff, group them into chains by related state or objects, and gather evidence and judge each chain. Reuse evidence across related branches, but assess different triggers and consequences separately; after finding an issue, continue checking the remaining changed paths. Cite concrete source locations without presuming defects or inventing business rules.

1. **Confirm the change**: read relevant entry points and implementations to verify the actual method signatures, existing contracts, and behavior before and after the change. Expected behavior may be based on interface contracts, design, tests, or explicit code invariants. For changes to validation ranges, defaults, or branches, separately verify whether newly accepted or rejected inputs match the change's intent. Do not treat existing tests as outdated merely because the implementation changed; record specific conflicts when the supporting evidence remains unresolved.
2. **Trace state chains**: first establish the contracts and read uses of key states involved in this change. Then trace each write entry point through "entry point → state reads and writes → guard → subsequent action", comparing trigger timing and separately judging whether state writes, subsequent admission, and side effects respect those contracts. Assess completion, exception, and cancellation entry points sharing a wrapper separately; their judgments are not interchangeable. For concurrency or async behavior, verify actual executing threads, scheduling boundaries, synchronous versus queued callbacks, and task termination ordering. If a state contract cannot be established, save the specific dispute in `unverified_items` under the output contract.
3. **Fill specific gaps**: read more only for a concrete gap that could change the judgment, first identifying the question and likely evidence source. For decisive library or framework calls, verify the target version's declaration, contract, or implementation. For model or cache reads, follow object acquisition and wrapping to confirm the actual implementation and relevant overrides; do not infer behavior from method names, same-name overloads, or default implementations. Search Git history only when a concrete historical lead could change the judgment. When a contract conflict cannot be resolved and there is no new lead, stop gathering more evidence, record it as unverified under the output contract, and state both sides' evidence and the behavioral consequences under each interpretation; do not rule out the issue by accepting only one side.
4. **Complete the judgment**: record each path as "confirmed issue", "ruled out with evidence", or "unverified with a specific gap". Exclusion conclusions cover only the consequences verified by their evidence. Assess other contracts, state meanings, and admission conditions on the same path separately; ruling out one risk does not rule out the entire path. For unverified paths, identify which step in the trigger, ordering, or consequence the gap affects. Distinguish "the supplied implementation supports the path" from "the target build version is confirmed"; retain unverified status when a version gap determines reachability, without dismissing existing evidence wholesale. Move to the next chain when complete, revisiting only when new evidence or a concrete counterexample could change the judgment.

## 2. Behavioral checks

For the main paths affected by this change, check with the entry points, callers, and context in mind:

- Do conditional branches behave as expected, and are there inverted or missing branches? When routing changes, compare the actual paths for the same input before and after the change, and include pre-existing defects triggered by the new path in this round's checks.
- Are state transitions allowed, and do side effects run under the correct conditions?
- Are nulls, empty collections, and numeric boundaries handled correctly?
- After an exception or partial failure, are state and resources handled correctly? For sequences involving databases, caches, messages, or external calls, check whether partial success, timeouts, or retries lead to inconsistent state or repeated side effects that violate the contract.

Choose applicable check directions and concrete counterexamples for each behavior chain, and reason through them:

- **Parsing / validation**: first confirm the input language and dependency versions, and proactively read the corresponding syntax or format contract; the current sample alone cannot stand for valid input. Choose valid equivalent forms per the contract, and check consistency along "parse → validate → use" and whether validation can be bypassed.
- **Serialization / template rendering**: follow the call chain to read the actual wrapping, rendering, and parsing implementations, and compare with the related old entry points. Trace variable values along the actual conversion order, choose inputs such as quotes, backslashes, or newlines, and check whether escaping or decoding changes the original value or breaks the structure.

**Concurrency and async check matrix**: when shared state, retries, or async tasks are involved, select applicable rows from the code signals in this change; a behavior chain may match multiple rows.

Read the applicable [interleaving examples](../concurrency-examples.md), map the actors, state, and interleaving points to actual source, and verify reachability and protection mechanisms; do not copy the example conclusions.

| Type and code signal | Core risk | Basis for exclusion |
| --- | --- | --- |
| Check-then-act: inspect a cache, state, or existence before acting | State changes before the action, including between separate critical sections | An atomic protocol preserves the action's precondition; rechecking another state must guarantee that precondition; individually locked accesses are insufficient |
| Read-modify-write: read, compute, write back | Concurrent updates overwrite each other | A lock, atomic operation, or suitably isolated transaction protects the whole operation |
| Visibility and publication: cross-thread initialization or readiness flags | Readiness is visible but data is incomplete or stale | Effective publication and visibility guarantees, or thread confinement |
| Cancellation and task termination: callbacks release busy/loading | A new task enters while the old task or subtasks still run | Verify state-query contracts, cleanup ordering, and new-task admission separately; result isolation rules out result overwrites only and does not by itself justify releasing busy/loading; cancellation notification is not task termination |
| Stale callbacks: old and new tasks share state | A late callback overwrites or clears new task state | Task identity/version checks, or effective ordering and isolation |
| Repeated execution: retries, duplicate messages or triggers | An operation required once runs repeatedly | Atomic claims, deduplication, or idempotency cover state and observable side effects; equal results alone are insufficient; contractually permitted repetition is not a defect |
| Deadlock: multiple locks or calls while holding a lock | Reverse lock ordering or circular waits | Lock ordering, avoiding waits while holding locks, or another guarantee prevents the cycle |

For operation races, give a concrete interleaving and state changes; for visibility/publication, explain the synchronization and publication guarantees. Apply section 1's evidence and judgment method. Do not enumerate every thread combination, force findings, or output the matrix; reuse the existing "actual check scope".

For other behavioral changes, choose counterexamples per the main paths.

## 3. Recording and reporting

Check records uniformly state:
**handling point location → trigger conditions and specific input → expected behavior and basis → relevant code path → actual behavior and consequence**.

Once the main paths have these judgments, reuse the records to assemble and write the probe JSON. Do not routinely expand dependencies or recheck judged paths while finishing. If new evidence, a concrete counterexample, or contradictory evidence could change a conclusion, return to the relevant chain for evidence gathering.
Save specific concerns that cannot yet be confirmed as defects in `unverified_items` under the output contract. In the return message, use the existing "actual check scope" to briefly state checked paths and other scope limitations; the return message does not replace JSON records.

Confirmed issues go into the finding's `evidence`; grading and contract-conflict handling follow the [output contract](../output-schema.md).
Record different root causes or consequences separately; do not merge them to evade grading. Save issues that depend on unresolved contract conflicts in `unverified_items` when no finding is created.
When the syntax basis, the actual implementation path, or the reachability of a valid triggering input has not been verified, state the specific gap and do not treat it as a proven defect.
Checks not completed or with insufficient evidence are listed as unverified items and limitations, not lumped into "checked"; when not run, mark "static reasoning" and do not call it reproduced.

Behavioral findings do not require an existing rule ID and are not subject to `repo-guard`'s HIGH-only reporting limit.
