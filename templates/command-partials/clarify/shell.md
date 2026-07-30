{{spec-kit-include: ../common/user-input.md}}

## Objective

Strengthen the current specification package just enough to remove planning-critical gaps and make the next planning decision better grounded.

## Context

- Primary inputs: the existing spec package, any newly supplied requirements or references, and the current repository context.
- The active working set is `spec.md`, `alignment.md`, `context.md`, `references.md`, `workflow-state.md`, `clarification/handoffs/`, `clarification/evidence-index.json`, and `clarification/checkpoints.ndjson` inside the current `FEATURE_DIR`.
- This command is enhancement-oriented. It should improve the package already on disk rather than restart the workflow from zero.

## Process

- Identify the specific planning-critical gaps or weak analysis that need improvement.
- Deepen the relevant parts of the specification package through targeted analysis or bounded research.
- Patch only targeted fields through their registered artifact CLI owners and reassess planning readiness.

## Output Contract

- Submit every improved spec-package section through its registered artifact CLI owner.
- Persist clarification lane evidence through CLI channels: workers use inline `result submit --command clarify`, the leader uses JSON-pointer `artifact patch` for `clarification/evidence-index.json`, and checkpoints use `artifact patch --append-json`.
- Query `clarification/evidence-index.json` through `specify-runtime artifact show` before final CLI-owned artifact updates.
- Query every accepted clarification handoff through `specify-runtime artifact show` before final updates; integrate it into `spec.md`, `alignment.md`, `context.md`, or `references.md` only through leased `artifact patch` calls, or patch an explicit deferral/blocker with its reason.
- Report what changed, what risks remain, and whether the package is ready for `/sp-plan`.
- Keep unresolved uncertainty explicit instead of implying false readiness.

## Guardrails

- Prefer targeted enhancement over a full restatement.
- Do not imply planning readiness if planning-critical ambiguity still remains.
- Do not rerun the whole `sp-specify` flow unless the current package is unusably wrong.
