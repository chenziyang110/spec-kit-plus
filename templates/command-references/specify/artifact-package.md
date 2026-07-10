Trigger: when writing or refreshing planning-ready specification outputs.

Purpose: keep one agent authority while retaining project-facing documents only when they provide independent review value.

Preserved Contract: confirmed scope, acceptance proof, decisions, evidence, fidelity, and consequence obligations remain planning-ready and traceable.

## Artifact Writing Contract

Write `spec-contract.json` first from `templates/spec-contract-template.json`.

- Store target need, in/out/deferred scope, constraints, objective acceptance criteria, locked decisions, `semantic_delta`, protected obligation refs, context capsule, unresolved items, artifact refs, and the agent phase transition.
- Render `spec.md` from the contract as the primary project-facing specification.
- Write `alignment.md` only when semantic mapping, upstream disposition, conflict, deferral, fidelity, or readiness analysis has content that maintainers need to review independently.
- Write `context.md` only when repository placement, reuse, integration, propagation, or boundary evidence cannot be represented adequately by stable refs in the context capsule.
- Write `references.md` only when external or retained references materially shape behavior or proof.
- Produce requirements diagnostics from deterministic validation; persist `checklists/requirements.md` only when compatibility or human review requires it.
- Keep `workflow-state.md` as sparse resume state, not a copy of specification truth.
- When compatibility requires `brainstorming/handoff-to-specify.json`, make it a pointer-only agent transition: `source_contract`, `review_digest`, `semantic_delta`, required refs, blockers, and next action.

Preserve reference fidelity and `CA-###`/`MP-*` obligations by stable ref. Copy a full obligation body only when the next phase cannot safely act from the reference.

## Extension Hooks

After the completion report, check whether `.specify/extensions.yml` exists.

- If it exists, read entries under `hooks.after_specify`.
- If YAML cannot be parsed, skip hook execution guidance silently.
- Filter out hooks where `enabled` is explicitly `false`.
- Treat hooks without `enabled` as enabled.
- Do not evaluate non-empty hook conditions directly; leave condition evaluation to the HookExecutor implementation.
{{spec-kit-include: ../../command-partials/common/extension-hooks-after-body.md}}
