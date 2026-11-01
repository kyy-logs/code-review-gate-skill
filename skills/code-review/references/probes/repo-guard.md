# probe: repo-guard (repository standards)

**required: true** | **requires: rules** | `read_only: true`

## 1. Select the rule pack

1. When `$CODE_REVIEW_RULES_DIR` is non-empty, use the specified path; if the path does not exist or is unreadable, record `error` and do not fall back.
2. When unspecified, use `<project root>/.code-review/rules/` if that directory exists; otherwise use the skill's built-in `references/rules/`.

First read the selected rule pack's `index.md` to learn the rule topics. A project-provided rule pack **entirely replaces** the built-in one; they are not merged.

## 2. Rule scanning and candidate review

The review scope and code version follow "Determine the review scope" in the main flow's `SKILL.md`.

1. **Select files**: choose `.java` / `.ts` / `.tsx` / `.vue` from the change list,
   including added files and excluding deleted files; when no applicable files exist, go to section 3.
2. **Run the scan**: pass the file paths one by one as independent arguments to
   `bash "$CODE_REVIEW_SKILL_DIR/scripts/rule-grep"`.
   The script scans the full file text, and hits may include old code.
3. **AI review**: with the corresponding rule, code context, and this round's diff, confirm whether a violation actually exists.
   Include only issues introduced or triggered by this change in the findings; record unrelated old issues separately and exclude them from this round's counts.

Rules that cannot be decided by pattern go to section 3.
When on-disk files differ from the review target version, read the target version's source and perform the AI semantic check per section 3.

The scan only provides candidates; a hit is not a violation, and a miss is not compliance.

## 3. On-demand loading and AI semantic checks

An AI semantic check means the AI reads the rule text, the diff, and the relevant code context to judge whether the rule applies and whether the code actually violates it.

Load the corresponding rule files on demand based on the index, project language, change topic, and scan hits.
Prose rules that cannot be machine-judged but are relevant to the change must also be loaded; do not check only the scan hits.
Default check topics include:

- SQL injection
- XSS
- Authentication and permission isolation
- Sensitive data handling
- Hardcoded credentials
- Idempotency

The specific requirements follow the rule files selected this round.

Compare each selected rule against this change, and note in the report the rule files actually loaded and the checked scope.
Produce findings only for HIGH-severity rules.
When a standards violation is found, record the **applicable rule ID, file, line number, and violation description**.

For general behavioral correctness checks, see [behavior-review](behavior-review.md).

## 4. Judgment and reporting

Record `error` when the rule pack directory does not exist or not a single rule file can be read.
