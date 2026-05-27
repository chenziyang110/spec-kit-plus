# Spec-Lint Contract Refresh Design

## Context

`tools/spec-lint/` and `templates/spec-quality-gate.md` last changed with the
2026-05-01 layered progressive disclosure work. Since then, the generated
`sp-*` workflow contracts have continued to evolve, especially around
`sp-specify`, discussion handoffs, adaptive planning/task execution, project
cognition, and must-preserve traceability.

The current `spec-lint` binary still validates the original eight tiered
quality checks:

- scout summary
- capability triage
- execution mode
- change propagation
- non-functional requirements
- error user-visible contract
- configuration effective-when
- test strategy

Those checks remain useful, but they no longer cover the current
`sp-specify -> sp-plan` planning-ready artifact contract. A spec package can
pass the old checks while missing the compatibility handoff, source signal
disposition, must-preserve ledger, planning gate status, or user review state
now required by `sp-specify`.

## Goal

Refresh `spec-lint` so it validates whether a `sp-specify` artifact package is
mechanically ready to hand to `sp-plan`.

The tool should remain a zero-dependency Go binary under `tools/spec-lint/`.
The command-line surface should stay stable:

```text
spec-lint -dir <FEATURE_DIR> -tier light|standard|deep
```

## Non-Goals

- Do not turn `spec-lint` into a generic configurable linter for every
  workflow.
- Do not implement full `sp-plan`, `sp-tasks`, adaptive execution, map, PRD,
  or implementation handoff validation in this pass.
- Do not add Python runtime dependencies or call into `specify` CLI internals.
- Do not add LLM-based judgment checks.
- Do not make every quality warning block planning readiness.

## Design

Add an artifact contract layer ahead of the existing quality heuristic checks.
The runner should still execute the tiered quality checks, but it should also
run `sp-specify -> sp-plan` readiness checks that understand the current
artifact set.

### Required Artifact Contract

The new contract layer should require these files to exist and be non-empty:

- `spec.md`
- `alignment.md`
- `context.md`
- `workflow-state.md`
- `checklists/requirements.md`
- `brainstorming/handoff-to-specify.json`

Missing required artifacts should be a failure.

### Workflow State Readiness

`workflow-state.md` should be parsed with conservative text checks. It should
fail when planning readiness cannot be established.

Required state:

- `active_command: sp-specify`
- completed or planning-ready status
- `last_user_reviewed_artifact_state: requested|approved`
- `source_signal_disposition_status: complete|not-applicable`
- `final_handoff_decision: /sp.plan` or a next command that resolves to
  `/sp.plan`

`last_user_reviewed_artifact_state: requested` should pass but emit a warning
that explicit user approval is not yet recorded. `approved` should pass cleanly.

### Handoff JSON Contract

`brainstorming/handoff-to-specify.json` should be parsed as JSON using Go's
standard library. The first implementation should validate the fields that are
needed by downstream planning, without overfitting to every possible future
field shape.

Required top-level fields:

- `status`
- `entry_source`
- `source_files_read`
- `source_signal_disposition`
- `must_preserve`
- `coverage_status`
- `planning_gate_status`
- `hard_unknown_count`
- `open_conflict_count`
- `quality_gate`

Failures:

- invalid JSON
- missing required fields
- `planning_gate_status` is not `ready`
- `coverage_status` is clearly incomplete
- `hard_unknown_count` is greater than zero
- `open_conflict_count` is greater than zero

Warnings:

- `quality_gate` exists but does not expose a readable status or summary
- `status` is present but not one of the currently recognized ready-ish values,
  when other planning gate fields are clean

### Source Signal Disposition

If `source_signal_disposition` is non-empty, each item must carry a recognizable
disposition.

Allowed dispositions:

- `preserved`
- `in_scope`
- `deferred`
- `dropped`
- `clarification_blocker`

Failures:

- a disposition item has no disposition
- a disposition uses an unknown value
- any item is marked `clarification_blocker` while the package claims
  `planning_gate_status: ready`

This check should be tolerant of object shapes. It may accept keys such as
`disposition`, `status`, or similarly direct fields, but it should not pass an
item that has no recognizable state.

### Must-Preserve Coverage

If `must_preserve` is non-empty, each item should have a stable trace field such
as `id`, `summary`, `signal`, or `description`.

Failures:

- a must-preserve row has no stable identifier or summary-like field
- a row is marked with an explicitly unmapped or unresolved state

This is a structural coverage check, not a semantic cross-document proof. It
should not attempt to prove that every item appears in `spec.md` in the first
iteration.

## Check Naming

Add new check names so failures are easy to act on:

- `required-artifacts`
- `workflow-state-readiness`
- `handoff-json-schema`
- `planning-gate-ready`
- `source-signal-disposition`
- `must-preserve-coverage`
- `review-state-approved`
- `quality-gate-summary`

The first six are readiness checks. The last two are warnings unless a stronger
failure is also present.

## Tests

Add real Go tests under `tools/spec-lint` so `go test ./...` exercises the
contract instead of reporting `[no test files]`.

Update `testdata/good-spec` to represent a current valid
`sp-specify -> sp-plan` package, including:

- `checklists/requirements.md`
- `brainstorming/handoff-to-specify.json`
- workflow state with planning-ready next command and user review state

Add targeted bad fixtures or test-generated temp directories for:

- missing handoff JSON
- invalid handoff JSON
- `planning_gate_status` not `ready`
- `hard_unknown_count > 0`
- `source_signal_disposition` containing `clarification_blocker`
- malformed or untraceable `must_preserve`
- workflow state missing user review gate
- workflow state routing to anything other than `/sp.plan`

Assertions should cover:

- good fixture exits cleanly
- bad fixtures return failures and include the expected check name
- warning-only cases exit cleanly while printing a warning

## Documentation Updates

Update `templates/spec-quality-gate.md` to describe the new artifact contract
gate before the existing tiered quality gate.

Update `PROJECT-HANDBOOK.md` so the `spec-lint` description no longer says only
that it validates eight tiered quality checks. The new description should say it
validates the `sp-specify -> sp-plan` artifact contract plus tiered quality
checks.

Review `README.md` for any `spec-lint` usage text and update it if it describes
the old eight-check-only model.

## Verification

Implementation should finish with:

```text
cd tools/spec-lint
go test ./...
go vet ./...
go build -o /dev/null .
```

Then run the smallest relevant repository-level tests that cover docs/template
alignment for touched surfaces.

## Open Risks

- The handoff JSON schema may keep evolving. The checks should validate fields
  needed for planning readiness without rejecting harmless future fields.
- Markdown parsing should stay conservative. The first pass should prefer
  explicit workflow-state keys over complex freeform inference.
- Must-preserve semantic coverage is important, but a full cross-document proof
  should be a later enhancement unless current tests expose a simple reliable
  pattern.
