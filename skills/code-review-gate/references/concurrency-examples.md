# Concurrency interleaving examples

These are constructed execution orders, not runtime records. Select relevant examples and verify the interleaving against concrete entry points, reads, writes, and contracts; similar structure alone does not establish a defect. The examples do not cover every matrix type or require every trace to be output.

## 1. Check-then-act: separately locked operations can oversell

Contract: stock must not become negative. The check and decrement each hold the same lock, but the decrement does not recheck.

```text
Initially: stock = 1.
A: acquire the lock, read stock > 0, release the lock.
B: acquire the lock, check stock > 0, decrement to 0, release the lock.
A: reacquire the lock, act on the earlier result, decrement to -1, release the lock.
```

Failure: A's check becomes stale before the action; locking individual reads and writes does not protect the compound operation.
Verify: check and decrement share one critical section, or an effective recheck, conditional update, or equivalent atomic protocol protects the action.

## 2. Cancellation and task termination: an old task writes after its guard is released

Contract: only one task may write to a resource at a time. Here, cancellation notification does not wait for termination, and old and new tasks share their result state.

```text
Initially: A is running, busy = true.
User: request cancellation of A.
Cancellation callback: busy = false; A has not exited.
User: start again; B passes the busy check and begins execution.
A: continue writing the shared result; B also starts writing it.
```

Failure: the guard admits a new task while the old task can still affect the same resource.
Verify: the old task and relevant subtasks have terminated before releasing the guard, or actual task isolation prevents the effect. Preventing the old task from publishing results only rules out the corresponding result-overwrite risk; whether busy/loading may be cleared still depends on that state's contract. Separately verify state accuracy and the conditions for admitting a new task.

## 3. Stale callbacks: an old request overwrites a new result

Contract: the page displays data for the current selection. Requests can complete out of order, and callbacks do not check request identity.

```text
User: select X and start request A.
User: switch to Y and start request B.
B: return first; the page displays the result for Y.
A: return later; its callback unconditionally updates the page with the result for X.
```

Failure: a callback from an old request changes the current page state.
Verify: request IDs or versions are checked before publishing results, or another actual guarantee prevents stale callbacks from taking effect; requesting cancellation alone does not establish that callbacks cannot run.

## 4. Correct control: rechecking under the lock prevents a stale decision

Contract: reuse cached results when available. Cache publication and the decision to start loading use the same lock.

```text
Initially: cache is empty.
A: read an empty cache under the lock, then release it.
B: publish cache = S under the lock, then release it.
A: enter the loading-decision critical section, recheck cache, find S, and decide to reuse it without starting a load.
```

Protection: A does not act on the stale empty-cache check; the decision uses the current cache under the lock.
The exclusion rests on the actual recheck and shared-lock protocol, not merely the presence of a lock. If another flag is checked instead, verify why it guarantees that the original action's precondition still holds.
