# probe: impact-analysis (impact analysis)

**required: false** | **requires: []**

Read [`common.md`](common.md) first; it defines the constraints shared by all probes.

Check this change's impact on callers, contracts, performance, and architecture.

## 1. Inbound callers of changed methods (fan-in)

For methods in this diff whose **signature or caller-visible behavior changed**, trace callers one by one:

Use the review scope and target version determined by the main flow.
Method declaration changes are only used to help locate; also check changes in return-value meaning, exceptions, and side effects caused by method body changes.
Call forms differ by language and must be confirmed against the actual code.

For methods involving the above changes, answer:

| Question | Why ask |
|---|---|
| Who calls it? (how many) | The larger the fan-in, the larger the blast radius of the change |
| Are callers **outside this repository**? | Cross-repository callers cannot change along with it, so the contract must stay compatible |
| Do callers also need changes? | When callers need adaptation but were not changed, describe the specific call path, trigger conditions, and consequences |
| Is an overload with the same name affected by mistake? | Overload resolution changes are a classic silent break |

`depth=1` (registry parameter): by default, trace only **one level** of callers.

## 2. Contract changes

- Were fields added, removed, or changed in external interfaces (HTTP / RPC / MQ message bodies)?
- Is the database schema change **backward compatible**? (nullable column added vs type change vs column dropped)
- Did config file / environment variable key names change? (multi-environment matrix, see the design doc)
- Did the serialization format change? (JSON field names, time format)

First confirm whether the change breaks an existing contract, and describe the affected call forms, data, or deployment conditions and the specific consequences,
then grade per the severity criteria in `references/output-schema.md`.
A compatible change is not graded high merely because no separate compatibility strategy was written.

## 3. Performance

Perform a static performance check on the paths involved in this change; it does not depend on whether a design doc is provided.

Focus areas: newly added in-loop queries / N+1, full table scans, unbounded collections,
synchronous blocking calls, cache breakdown, and batch sizes for bulk operations.

When caches or proxies are involved, trace to the actual I/O boundary; without confirming database access, do not equate the number of method calls with the number of new SQL queries.

If the design doc has performance targets, compare them against the relevant implementation, and judge whether targets are met only when corresponding measured data exists.
When design targets or measured data are missing, record the verification limitation and do not fail it merely for missing material;
when targets exist but no measured data does, note "performance targets unverified" and do not claim they are met based on code inspection alone.

This probe does not run load tests automatically. When a risk is found, describe the specific code path,
the applicable data scale or call conditions, and the possible consequences.

## 4. Architectural impact

For modules and related call/dependency paths involved in this change, check against the project's existing architectural conventions:

- Is unrelated responsibility crammed into the same module?
- Are circular dependencies introduced, or the project's existing dependency direction broken?
- After a public interface change, can existing implementations or callers still be replaced and used normally?
- Do new abstractions and intermediate layers serve the current need?

When a problem is found, cite the specific module, dependency, or call path, and describe the affected contract or constraint and the actual consequence.
Do not rate it high risk merely for "not following some design principle", and do not force the project to adopt a fixed layering.
Things that are only structural optimization suggestions without proven concrete breaking impact are recorded separately as non-blocking suggestions.

## 5. Anti-patterns

- ❌ Reporting high just because a method name changed, without confirming whether there are callers — that is noise and drowns out real problems
- ❌ Checking only in-repository callers and ignoring **external** consumers of external interfaces
- ❌ Treating "someone could theoretically call it" as a finding (it must be **specific** about which caller)
