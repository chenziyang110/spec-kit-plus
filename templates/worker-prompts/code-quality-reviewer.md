## Fixed Workflow Artifact Boundary

Read canonical workflow artifacts only with `specify-runtime artifact show`. When the worker packet authorizes an artifact mutation, use the specialized owner named by the artifact registry or packet. Generic `artifact prepare` plus `artifact submit` is valid only when prepare explicitly grants submit for that type; fixed-shape artifacts use scaffold plus targeted patch, and result/evidence artifacts use their namespaces. Never overwrite the canonical path directly. Source and test files in the packet's write scope remain normal repository edits.

# Code Quality Reviewer Worker Prompt

## Output Asset Scope

Create ancillary documents, reports, or media only within the assignment's authorized output scope. Use the leader's exact paths or `specify-runtime assets route` inputs; temporary output carries task/worker identity and retention. Preserve source/native filenames, canonical artifact owners, and the existing inline/runtime result channel. Reading a file does not authorize relocating it. Return the exact changed asset paths and any unavailable checks to the leader for one combined `assets check`; do not generate side reports, shared indexes, or workflow state merely to document this worker run.

> Legacy compatibility prompt. New `sp-implement` ordinary task reviews use `.specify/templates/worker-prompts/task-reviewer.md`, which returns both `spec_verdict` and `quality_verdict` in one result.

Use this template when the leader needs an independent quality review after spec review passes.

## Review Order

- Only run after spec review passes.
- Review implementation quality, not requirement fit.

## Review Questions

- Does each changed file have one clear responsibility?
- Did this change preserve file responsibility instead of smearing logic across surfaces?
- Are names, tests, and interfaces maintainable?
- Did the worker create unnecessary complexity or fragile coupling?

## Output Format

- Strengths
- Issues by severity
- File references
- Final assessment
