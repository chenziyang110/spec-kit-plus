{{spec-kit-include: ../common/user-input.md}}

## Objective

Generate a complete graph-native evidence baseline for the current codebase.

## Context

- Primary inputs: git-baseline diff data when available, live repository surfaces, existing reference artifacts, passive learning files as read-only workflow guidance, not scan evidence, and optional focus hints from `$ARGUMENTS`.
- This command owns graph-native evidence-baseline outputs only; it must not write final cognition truth.
- Legacy atlas artifacts such as `PROJECT-HANDBOOK.md` may be read only when explicitly relevant to migration or export parity; they must not become scan targets.
- `.specify/**` is workflow/runtime state, not project graph evidence; `.specify/**` paths may be read only for command operation or validation and must not become scan targets or graph paths.
- Apply project cognition ignore rules from root `.cognitionignore` and `.specify/project-cognition/.cognitionignore` before accepting repository-universe, evidence, coverage, or packet scope. These files use gitignore-compatible patterns for project cognition only.
- Before subagent dispatch, write the canonical boundary in `.specify/project-cognition/workbench/repository-universe.json`; do not rely on user-maintained `.cognitionignore` as the primary boundary mechanism.
- Treat `.cognitionignore` as an override source recorded in `decision_source`; excluded paths stay in boundary accounting and out of graph-facing coverage.
- The resulting evidence baseline must let `sp-map-build` reconstruct the project cognition graph from live-surface evidence without inventing scan scope.
- Maintain `.specify/project-cognition/status.json` as the baseline state surface for graph-native cognition readiness.
- If native subagent dispatch is unavailable or a substantive scan lane cannot complete, persist `subagent_blocked` in machine-readable state and block baseline activation until recovery. `coverage-ledger.json.open_gaps[]` may use `low_risk_open_gap` only with owner, reason, evidence expectation, and revisit condition.
