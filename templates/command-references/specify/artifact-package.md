Trigger: when writing or refreshing the planning-ready specification package.

Purpose: preserve artifact package content, compatibility handoff fields, extension hooks, and generated output expectations.

Preserved Contract: spec.md, alignment.md, context.md, references.md, workflow-state.md, requirements checklist, and compatibility handoff fields stay intact.

## Artifact Writing Contract

Write the specification package after context intake, necessary clarification, semantic decomposition, approach comparison, and section approval.

- `spec.md` must capture the product requirement in planning-ready form with confirmed scope, scenarios, capability decomposition, requirements, acceptance proof, decision capture, and risks.
- `alignment.md` must capture current understanding, confirmed facts, assumptions, open questions, `Semantic Term Decisions`, `Upstream Intent Disposition`, `Out-Of-Scope Conflicts`, must-preserve coverage, and readiness decision.
- `context.md` must capture planning context, repository context, reuse notes, integration boundaries, product constraints, change propagation, locked decisions, canonical references, open questions, and deferred ideas.
- When the source is `sp-discussion`, `spec.md`, `alignment.md`, and `context.md` must preserve the `Discussion Decision Digest`: selected direction, rejected alternatives, accepted tradeoffs, experience commitments, review criteria carried forward, and must-not-dilute constraints.
- `references.md` is optional and should be written when external docs, repository examples, issue links, discussion artifacts, or user-provided references materially shaped the spec.
- `workflow-state.md` must record current stage, review state, source-file sweep status, source-signal disposition status, final handoff decision, and next command.
- `checklists/requirements.md` must exist for first-release compatibility and must validate the written spec, not resurrect legacy state machinery.
- `brainstorming/handoff-to-specify.json` must exist as a minimal compatibility handoff for downstream commands. It must include:
  - `version`
  - `status`
  - `entry_source`
  - `discussion_slug`
  - `source_handoff`
  - `source_handoff_json`
  - `review_digest`
  - `source_files_read`
  - `source_signal_disposition`
  - `discussion_decision_digest`
  - `must_preserve`
  - `coverage_status`
  - `planning_gate_status`
  - `hard_unknown_count`
  - `open_conflict_count`
  - `quality_gate`
- Preserve fidelity requirements and reference behavior inventory when the feature is reference-sensitive or rewrite-style.
- Preserve Senior Consequence Analysis Gate outputs as `CA-###` obligations when triggered: affected object map, state-behavior matrix, dependency impact table, recovery and validation contract, coverage gaps, lifecycle operations, running state behavior, destructive operations, shared state, downstream consumers, and stand-down reason.

## Extension Hooks

After the completion report, check whether `.specify/extensions.yml` exists.

- If it exists, read entries under `hooks.after_specify`.
- If YAML cannot be parsed, skip hook execution guidance silently.
- Filter out hooks where `enabled` is explicitly `false`.
- Treat hooks without `enabled` as enabled.
- Do not evaluate non-empty hook conditions directly; leave condition evaluation to the HookExecutor implementation.
{{spec-kit-include: ../../command-partials/common/extension-hooks-after-body.md}}
