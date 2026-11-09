# Shared probe constraints

Read this file before the probe-specific document. These rules apply to every probe; the main flow includes this path in each dispatch and does not repeat the rules in each probe document.

## Role

- Check only your own probe. Do not re-run the whole review workflow and do not dispatch further agents.
- Reuse the scope, diff, and material confirmed and handed off by the main executor, together with context you have already read.

## Evidence and findings

- A finding must explain how this change introduced or triggered the issue. Describe unrelated pre-existing issues separately; they are not part of this round's finding list or counts.
- Merge independent read-only queries where possible, run dependent queries step by step, and preserve accurate line numbers and necessary context on first reads of source.
- Limit local searches to the reviewed repository, explicitly provided related directories, and cache paths corresponding to dependency coordinates. Start with changed files and known relevant directories, narrow by file type, and return only paths when locating files. For commit reviews, prefer `git grep <head> -- <paths>` to search the fixed target's tracked files; for worktree searches, use `rg` and exclude review output directories from source searches.
- When locating callers, combine known method, type, and factory names in a scoped source/test search and reuse its matches and no-match scope. Expand only for a specific evidence gap with a new symbol or path lead; if the caller is outside the supplied repository, record that gap and continue the other behavior chains. Do not repeat equivalent searches or expand to the disk root or user directory.

## Output

- Write only `{output_root}/active/{slug}/probes/<probe-name>.json`; do not write shared reports or metrics.
- Once checks are complete, first wait for any background tasks you started to finish, or stop tasks that are no longer needed and confirm they have exited. Then validate against `references/output-schema.md`, save the final JSON, and immediately return the handoff message. After saving, do not search, gather more evidence, or repeat explanations of findings.
- Record `duration` when reliable timing is available; the sum of per-probe durations does not represent the round's wall-clock time.

## Return message

State only the JSON path, the actual checked scope, and necessary limitations, including specific evidence gaps. The main executor incorporates them into the final report; do not repeat the findings in prose. The return message does not replace the JSON records.
