# Rule pack

This index lists the built-in rule files and their purposes; see the [repo-guard probe](../probes/repo-guard.md) for the loading and checking flow.

## Location priority

1. `$CODE_REVIEW_RULES_DIR`
2. Project root `.code-review/rules/`
3. Skill built-in: `references/rules/`

A project-provided rule pack replaces the built-in pack entirely (it is not merged). `bash "$CODE_REVIEW_SKILL_DIR/scripts/rule-grep"` uses the same priority order.

## Built-in files

| File | Type | Content |
|---|---|---|
| `baseline-java.md` | Machine-checkable / semantic check | 9 baseline rules |
| `concurrency.md` | Prose | Thread pools, SimpleDateFormat, lock ordering |
| `exception-logging.md` | Prose | Exception catching, transaction rollback, logging |
| `naming-format.md` | Prose | Naming and formatting |
| `oop-collection.md` | Prose | Immutability, defensive programming, collections |
| `spring-performance.md` | Prose | Spring / JPA / transactions / performance |
| `testing-engineering.md` | Prose | Unit-test conventions |
| `security.md` | Prose | Security baseline |

## Rule file format

Each rule has one heading, followed by an optional `Detection pattern` line:

```markdown
### SEC-001 [HIGH] SQL string concatenation

Why this rule matters.

**Detection pattern** (any hit is a violation):
- `regex-one`
- `regex-two`
```

- The heading must be `### <rule-id> [<severity>] <title>`; the severity is one of `HIGH` / `MEDIUM` / `LOW`
- Backtick fragments in `Detection pattern` are extracted by `bash "$CODE_REVIEW_SKILL_DIR/scripts/rule-grep"` and run as regexes
- Rules without a detection pattern do not participate in regex scanning
- **The rule ID is the finding's evidence**; a judgment without an ID does not count
- Legacy localized rule packs may use their own detection-marker label; `rule-grep` accepts the supported aliases

## Constraints

- Only write your team's own rules; do not copy internal standards of unknown origin
- Keep regexes as narrow as possible; prefer missing a hit over producing many false positives
