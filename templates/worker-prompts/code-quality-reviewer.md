## Fixed Workflow Artifact Boundary

Read canonical workflow artifacts only with `specify-runtime artifact show`. When the worker packet authorizes an artifact mutation, use the specialized owner named by the artifact registry or packet. Generic `artifact prepare` plus `artifact submit` is valid only when prepare explicitly grants submit for that type; fixed-shape artifacts use scaffold plus targeted patch, and result/evidence artifacts use their namespaces. Never overwrite the canonical path directly. Source and test files in the packet's write scope remain normal repository edits.

# Code Quality Reviewer Worker Prompt

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
