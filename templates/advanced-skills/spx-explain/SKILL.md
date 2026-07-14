---
name: spx-explain
description: Read-only workflow-artifact explanation for advanced coding models. Use when the user wants a spec, plan, tasks, lane state, cognition state, or compatibility artifact explained from what is actually on disk.
---

# SPX Explain

Read `references/project-cognition.md`, using cognition intent `ask`, and
`references/artifact-explanation.md`.

Resolve the active feature or lane before guessing. Read the most downstream
artifact that directly answers the question, then only its authoritative inputs
and the live repository evidence needed to distinguish intent from current
behavior.

Explain the artifact's purpose, important decisions, relationships, consequences,
readiness, and unresolved gaps in the user's language. Prefer a compact mental
model over section-by-section paraphrase. Clearly separate what the artifact
claims, what the repository currently proves, and what remains unknown.

Remain read-only. Do not rewrite artifacts, update lifecycle state, create
reports, or advance to another workflow unless the user separately requests
action. On a follow-up about the same artifact, reuse still-current evidence and
read only the delta.
