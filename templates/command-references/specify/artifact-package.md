Trigger: when writing or refreshing planning-ready specification outputs.

Purpose: keep one agent authority while retaining project-facing documents only when they provide independent review value.

Preserved Contract: confirmed scope, acceptance proof, decisions, evidence, fidelity, and consequence obligations remain planning-ready and traceable.

## Artifact Writing Contract

Create `spec-contract.json` first through `specify-runtime artifact scaffold --kind spec-contract`, which owns the fixed `templates/spec-contract-template.json` shape; use leased `artifact patch` for pointer updates.

- Store target need, in/out/deferred scope, constraints, objective acceptance criteria, locked decisions, `semantic_delta`, protected obligation refs, context capsule, unresolved items, artifact refs, and the agent phase transition.
- Store `acceptance_coverage` as unique one-pair rows from canonical `scope.in` or `capability_operations` JSON Pointers to canonical `acceptance_criteria` JSON Pointers. Every requirement must appear at least once; every criterion must appear exactly once and therefore cannot close multiple independent requirements.
- Query the prerequisite-script-created `spec.md` skeleton through `artifact show` and fill only named sections through leased `artifact patch --section`; never emit or resubmit the stable template.
- When `alignment.md` has independent review value, create an absent file with `specify-runtime artifact scaffold --kind alignment`, then fill only named sections through fresh leased `artifact patch` calls; never submit the stable template wholesale.
- The prerequisite script normally creates `context.md`. Query that skeleton and patch only named sections when repository placement, reuse, integration, propagation, or boundary evidence has independent value; recover a missing skeleton with `artifact scaffold --kind specify-context`, never a full-document submission.
- When retained references materially shape behavior or proof, create an absent `references.md` with `artifact scaffold --kind references`, then patch its named sections; never reproduce the installed template in memory.
- Produce requirements diagnostics from deterministic validation. When compatibility or human review requires `checklists/requirements.md`, send one compact checklist object to `specify-runtime artifact checklist`; the CLI expands the template and assigns `CHK###` IDs. Never submit checklist Markdown wholesale.
- Keep `workflow-state.md` as sparse resume state, not a copy of specification truth.
- When compile mode requires `brainstorming/handoff-to-specify.json`, call `specify-runtime discussion bind-consumer` with only the agent-owned transition fields. The runtime derives `source_contract`, `review_digest`, status, and next action and writes the pointer.

Preserve reference fidelity and `CA-###`/`MP-*` obligations by stable ref. Copy a full obligation body only when the next phase cannot safely act from the reference.

## Extension Hooks

After the completion report, run `{{specify-subcmd:specify-runtime hook extension-plan --event after_specify --format json}}`; never inspect extension storage. Offer each returned `optional: true` invocation, execute each returned `optional: false` invocation, and continue silently when `actionable_count` is zero.
