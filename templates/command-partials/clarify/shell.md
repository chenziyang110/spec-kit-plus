{{spec-kit-include: ../common/user-input.md}}

## Objective

Strengthen the current specification package just enough to remove planning-critical gaps and make the next planning decision better grounded.

## Context

- Primary inputs: the existing spec package, any newly supplied requirements or references, and the current repository context.
- The active working set is `spec.md`, `alignment.md`, `context.md`, and `references.md` inside the current `FEATURE_DIR`.
- This command is enhancement-oriented. It should improve the package already on disk rather than restart the workflow from zero.

## Process

- Identify the specific planning-critical gaps or weak analysis that need improvement.
- Deepen the relevant parts of the specification package through targeted analysis or bounded research.
- Update the artifact set in place and reassess planning readiness.

## Output Contract

- Write the improved spec package back to disk.
- Report what changed, what risks remain, and whether the package is ready for `/sp-plan`.
- Keep unresolved uncertainty explicit instead of implying false readiness.

## Guardrails

- Prefer targeted enhancement over a full restatement.
- Do not imply planning readiness if planning-critical ambiguity still remains.
- Do not rerun the whole `sp-specify` flow unless the current package is unusably wrong.
