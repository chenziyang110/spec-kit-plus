{{spec-kit-include: ../common/user-input.md}}

## Objective

Generate a complete graph-native evidence baseline for the current codebase.

## Context

- Primary inputs: git-baseline diff data when available, live repository surfaces, existing reference artifacts, passive learning files as read-only workflow guidance, not scan evidence, and optional focus hints from `$ARGUMENTS`.
- This command owns graph-native evidence-baseline outputs only; it must not write final cognition truth.
- Legacy atlas artifacts such as `PROJECT-HANDBOOK.md` may be read only when explicitly relevant to migration or export parity; they must not become scan targets.
- `.specify/**` is workflow/runtime state, not project graph evidence; `.specify/**` paths may be read only for command operation or validation and must not become scan targets or graph paths.
- Resolve the candidate scan set through `specify-runtime cognition scan-set` before repository inventory, evidence, coverage, or packet scope. The runtime applies project cognition ignore rules from root `.cognitionignore` and `.specify/project-cognition/.cognitionignore`, built-in low-signal exclusions, binary-file suppression, and obvious secret-path suppression. These rules are for project cognition only.
- Run `scan-formats`; the Agent proposes cohort-level decisions for
  every runtime-issued `cohort_id`. The Agent must not submit path-level
  overrides. Stage the complete proposal with `scan-policy-stage`, present its
  bounded representatives and summary, and wait until the user confirms the
  exact `proposal_digest` before `scan-policy-confirm`. If the runtime reports
  `format inventory changed`, restart this policy cycle. scan-prepare requires
  the confirmed policy and rejects missing, tampered, stale, or incomplete
  decisions.
- Before subagent dispatch, run `scan-prepare` so the runtime detects file
  formats first, then materializes the canonical value-weighted target set from
  the resolved scan-set file. Directory and Git state are guardrails after
  format detection, not proof that an unknown path is source code. Audit those
  projections, but do not hand-write or repair them. Do not
  substitute raw `rg --files`, broad directory globs, or free-form agent
  judgment about what to omit.
- Treat `scan-prepare` as resumable and incremental. The same
  `preparation_digest` resumes accepted/pending work. After `validate-scan`,
  unchanged content-SHA-256 plus effective-policy and scan-contract matches are
  replayed as current-generation `reuse-*` packets; dispatch only the returned
  `pending_path_count`. Never reuse old packet, attempt, or receipt identity.
  Cross-path dependencies share one invalidation scope, so workers must record
  shared nodes, cross-path edges, and multi-path evidence or claims explicitly.
  Cache lineage must cover every current accepted packet/path before automatic
  generation replacement; older cache cannot discard newer unvalidated work.
  Use `--full-rebuild`
  only for an explicit no-reuse rebuild; `--force` replaces an incompatible
  workbench but may still use validated cache bundles.
- Project cognition serves code understanding, change, and verification. By
  default `scan-prepare` keeps normal untracked source eligible while assigning
  untracked `.gitignore` matches, local runtime vendor/data/log payloads, and
  generated agent/workflow artifacts to inventory-only `P3`. Use
  `--include-gitignored` only for reviewed ignored source that is genuinely part
  of the code evidence; known low-signal artifact families remain inventory-only.
- Let deterministic format recognition construct repository cohorts. Use Agent
  assistance to propose scan depth for known and custom formats and to extract
  behavior, ownership, dependencies, and graph evidence from the confirmed
  semantic-scan cohorts. Review only bounded representatives; do not infer
  permission to read every file from a representative sample.
- [AGENT] Treat `scan-queue.json` and `handoff-ledger.json` as required scan workbench artifacts before `validate-scan`.
- Require the runtime-materialized canonical boundary and target artifacts
  before dispatch. Then accept scan packets only after the leader verifies
  packet-local ledger accounting for every assigned path and a
  `worker-results/<packet-id>.json` handoff whose `paths_read` is a non-empty
  concrete path array. Inventory-only paths receive no packet or graph-facing
  coverage row.
- Machine contract: each `worker-results/<packet-id>.json` handoff must put the packet-local ledger in top-level `ledger` with `todo`, `doing`, `done`, `blocked`, and `overflow`; do not write `packet_local_ledger`, `packet-local-ledger`, or Markdown-only ledger sections.
- Treat `.cognitionignore` and `scan-set` runtime exclusions as boundary sources recorded in `decision_source`; excluded paths stay in boundary accounting and out of graph-facing coverage.
- The resulting evidence baseline must let `sp-map-build` reconstruct the project cognition graph from live-surface evidence without inventing scan scope.
- Maintain `.specify/project-cognition/status.json` only through `specify-runtime cognition` status/checkpoint/finalization commands as the baseline state surface for graph-native cognition readiness.
- If native subagent dispatch is unavailable or a substantive scan lane cannot complete, record `subagent_blocked` through a leased `specify-runtime artifact patch` against `workflow-state.md`; yield or requeue any active attempt through the cognition CLI and block baseline activation until recovery. Do not patch `coverage-ledger.json` directly; only runtime-accepted packet results may materialize an open gap, including `low_risk_open_gap` with owner, reason, evidence expectation, and revisit condition.

## Ignore Configuration Gate

- Before repository inventory, run:

```text
{{specify-subcmd:specify-runtime cognition generate-ignore --format json}}
```

- If the command returns `review_required=true`, present its returned `suggested_patterns` to the user and wait for confirmation before continuing to inventory, packet dispatch, or writing `repository-universe.json`. After approval, use `{{specify-subcmd:specify-runtime cognition confirm-ignore --all-suggested --format json}}` only when every returned suggestion was approved; otherwise activate the approved subset with repeated `--pattern <exact-returned-pattern>` flags. Require `status=confirmed` before continuing. A created starter with `review_required=false` has no decision-bearing suggestions and needs no confirmation. Do not open `.specify/project-cognition/.cognitionignore` directly or edit it; creation, review intake, and activation stay on the cognition CLI.
- Treat commented starter suggestions as inactive. They are review prompts, not exclusions, until `confirm-ignore` records the review and activates an approved pattern.
- User chat confirmation alone is not an active rule. Only `confirm-ignore` or a pre-existing user-authored active rule can change the scan boundary.
- Preserve root `.cognitionignore` and existing `.specify/project-cognition/.cognitionignore` content; `generate-ignore` must not overwrite an existing ignore file.

After the ignore gate is clear, resolve the agent-facing candidate file list:

```text
{{specify-subcmd:specify-runtime cognition scan-set --out .specify/project-cognition/tmp/scan-files.json --format json}}
```

- Default stdout is compact JSON containing only the scan-set file path and count.
- The handoff file is a temporary agent-facing scan-set containing only `files`.
- If focus hints from `$ARGUMENTS` intentionally narrow the scan, pass them as concrete repeated `--scope` values and rerun `scan-set`; do not narrow by deleting paths from the resolved file manually.

Inventory repository-specific format cohorts:

```text
{{specify-subcmd:specify-runtime cognition scan-formats --format json}}
```

The Agent proposes cohort-level decisions covering every returned `cohort_id`
exactly once, with one short reason per cohort. It must not submit path-level
overrides. Stage that complete proposal:

```text
{{specify-subcmd:specify-runtime cognition scan-policy-stage --proposal-json '<inline-json>' --format json}}
```

Present the staged summary and bounded representatives. After the user confirms
the exact `proposal_digest`, activate only that proposal:

```text
{{specify-subcmd:specify-runtime cognition scan-policy-confirm --proposal-digest <exact-digest> --format json}}
```

If the runtime reports `format inventory changed` while staging or confirming,
restart at `scan-formats`. After confirmation, content or membership drift
inside a known cohort reuses its decision; a reported new format cohort requires
a new Agent proposal and exact confirmation.
`split_required` must be refined before confirmation. Chat approval alone is
not an active scan policy, and scan-prepare requires the confirmed policy.
