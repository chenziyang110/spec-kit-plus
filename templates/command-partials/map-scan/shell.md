{{spec-kit-include: ../common/user-input.md}}

## Objective

Generate a complete graph-native evidence baseline for the current codebase.

## Context

- Primary inputs: git-baseline diff data when available, live repository surfaces, existing reference artifacts, passive learning files as read-only workflow guidance, not scan evidence, and optional focus hints from `$ARGUMENTS`.
- This command owns graph-native evidence-baseline outputs only; it must not write final cognition truth.
- Legacy atlas artifacts such as `PROJECT-HANDBOOK.md` may be read only when explicitly relevant to migration or export parity; they must not become scan targets.
- `.specify/**` is workflow/runtime state, not project graph evidence; `.specify/**` paths may be read only for command operation or validation and must not become scan targets or graph paths.
- Resolve the candidate scan set through `project-cognition scan-set` before repository inventory, evidence, coverage, or packet scope. The runtime applies project cognition ignore rules from root `.cognitionignore` and `.specify/project-cognition/.cognitionignore`, built-in low-signal exclusions, binary-file suppression, and obvious secret-path suppression. These rules are for project cognition only.
- Before subagent dispatch, write the canonical boundary in `.specify/project-cognition/workbench/repository-universe.json` from the resolved scan-set file; do not substitute raw `rg --files`, broad directory globs, or free-form agent judgment about what to omit.
- [AGENT] Treat `scan-queue.json` and `handoff-ledger.json` as required scan workbench artifacts before `validate-scan`.
- Stage the canonical boundary artifact before dispatch, then accept scan packets only after the leader verifies packet-local ledger accounting for every assigned path and a `worker-results/<packet-id>.json` handoff whose `paths_read` is a non-empty concrete path array.
- Machine contract: each `worker-results/<packet-id>.json` handoff must put the packet-local ledger in top-level `ledger` with `todo`, `doing`, `done`, `blocked`, and `overflow`; do not write `packet_local_ledger`, `packet-local-ledger`, or Markdown-only ledger sections.
- Treat `.cognitionignore` and `scan-set` runtime exclusions as boundary sources recorded in `decision_source`; excluded paths stay in boundary accounting and out of graph-facing coverage.
- The resulting evidence baseline must let `sp-map-build` reconstruct the project cognition graph from live-surface evidence without inventing scan scope.
- Maintain `.specify/project-cognition/status.json` as the baseline state surface for graph-native cognition readiness.
- If native subagent dispatch is unavailable or a substantive scan lane cannot complete, persist `subagent_blocked` in machine-readable state and block baseline activation until recovery. `coverage-ledger.json.open_gaps[]` may use `low_risk_open_gap` only with owner, reason, evidence expectation, and revisit condition.

## Ignore Configuration Gate

- Before repository inventory, run:

```text
{{specify-subcmd:project-cognition generate-ignore --format json}}
```

- If the command returns `status=created`, review `.specify/project-cognition/.cognitionignore` with the user and wait for confirmation before continuing to inventory, packet dispatch, or writing `repository-universe.json`.
- Treat commented starter suggestions as inactive. They are review prompts, not exclusions, until the user removes the comment marker.
- Preserve root `.cognitionignore` and existing `.specify/project-cognition/.cognitionignore` content; `generate-ignore` must not overwrite an existing ignore file.

After the ignore gate is clear, resolve the agent-facing candidate file list:

```text
{{specify-subcmd:project-cognition scan-set --out .specify/project-cognition/tmp/scan-files.json --format json}}
```

- Default stdout is compact JSON containing only the scan-set file path and count.
- The handoff file is a temporary agent-facing scan-set containing only `files`.
- If focus hints from `$ARGUMENTS` intentionally narrow the scan, pass them as concrete repeated `--scope` values and rerun `scan-set`; do not narrow by deleting paths from the resolved file manually.
