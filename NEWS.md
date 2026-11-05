# News

User-facing changes, newest release first. Add each release under a `##`
heading; use `###` for categories. The latest released version (not the
Unreleased block) is automatically shown in the README. Keep internal plans
and evaluation artifacts out of this file.

<!-- UNRELEASED:START -->
## Unreleased

### Added

- code-review: surface unverified items and tighten behavior checks
- release: publish stable versions after validated VERSION changes

### Fixed

- code-review: return immediately after saving probe JSON

<!-- UNRELEASED:END -->

## v0.1.0 (2026-11-03)

### Added

- English and Chinese skill packages with shared runtime scripts and language-selectable installation for Claude Code and Codex.
- A canonical JSON-derived delivery summary, with report validation before gate decisions.
- Readable review reports: conclusions first, explanatory finding descriptions and fix suggestions, with full evidence collapsed at the end of each finding.

### Changed

- Organized behavior checks around changed paths, shared-state transitions, and applicable concurrency or async scenarios; reuse evidence and stop when the specific question is resolved.
- Clarified shared search boundaries, dependency evidence handoff, and test coverage measurement handoff.
- Strengthened static test-quality guidance for assertions, mocks, exceptions, and observable side effects.

### Fixed

- Portable runtime execution and project-level output and coverage configuration.
- Localized report labels, rule extraction, and false-positive status rendering.
- Severity guidance for confirmed local behavioral defects and unresolved contract conflicts.

### Validation and scope

- 87 offline tests passed locally with Bash enabled, covering installation, bilingual structure, JSON records, report rendering, and gates.
- Static-first review with four probes; no independent reviewer.
- This release does not establish general defect recall, false-positive rates, or reliable concurrency-defect detection. Tests, CI, and human review remain necessary.
- Earlier four-level records containing critical are incompatible; re-review or migrate explicitly.

## v0.1.0-beta.3 (2026-10-31)

### Removed

- Removed the independent reviewer and its Claude Code/Codex adapters. The four
  probes now feed the report and gate directly from raw findings; `reviewer.json`,
  `review-mode`, and reviewer-adapter installation are no longer used.

### Changed

- The installer now installs only the host skill layout. `--agent` selects the
  Claude Code or Codex skill directory, not a reviewer adapter.

## v0.1.0-beta.2 (2026-10-31)

### Added

- Parallel four-probe execution: each probe gets a fresh agent and writes its
  own JSON; hosts without four slots run in batches or record a serial fallback.
- Automatic NEWS unreleased updates and one-command remote skill installation.

### Changed

- Probe dispatch now includes bounded local-search and background-task cleanup
  rules, and `behavior-review` starts from the diff and stops when evidence is
  sufficient.
- `test-coverage` hands valid measured coverage back to the main executor;
  cross-probe duplicates remain separate records until a later deduplication
  design is adopted.

### Fixed

- `behavior-review` now checks asynchronous completion, exception, and
  cancellation cleanup paths and distinguishes a cancel notification from the
  task actually stopping.

### Validation

- Same-version reviews showed lower wall-clock time with four parallel probes:
  Keycloak about 2.5x, x01 about 2.9x, and the x01 impact-only repeat about
  2.7x.
- Token usage did not improve consistently, and target recall did not increase
  (the x01 impact target was found in 1 of 3 serial and 1 of 3 parallel runs).
  These are small samples; this is not a general speed or recall claim.

## v0.1.0-beta (2026-10-30)

### Added

- Four review probes: behavior correctness, test coverage, repository rules,
  and impact analysis.
- Portable skill source in `skills/code-review/`, with separate Claude Code
  and Codex reviewer adapters in `adapters/`.
- JSON-derived report sections and merge gates, with an optional independent
  reviewer.
- A unified installer for `claude-code`, `codex`, or both, with dry-run,
  conflict protection, and timestamped backups under `--force`.

### Changed

- Severity now uses three levels: `high`, `medium`, and `low`. Earlier
  four-level records require an explicit migration or a new review.
- Findings that depend on an unresolved contract conflict are capped at
  `medium` and marked as requiring contract confirmation.

### Packaging

- Added an MIT license, version file, and offline regression tests.
- Internal design documents and evaluation artifacts stay outside the
  published tree.
