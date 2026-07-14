---
name: spx-debug
description: Lean evidence-driven debugging workflow for advanced coding models. Use for a bug, regression, failed verification, or unexpected runtime behavior whose root cause is not yet proven.
---

# SPX Debug

Read `references/project-cognition.md`, using cognition intent `debug`.
Read `references/investigation-contract.md`. Read
`references/investigator-worker.md` only for delegated evidence. Resolve
`assets/debug-session.md` relative to this Skill when persistence is needed.
Read `references/consequence-gate.md` when the suspected cause or fix touches
lifecycle, shared state, destructive behavior, compatibility, migration,
security, concurrency, retry, recovery, or generated consumers.
Read `references/ui-quality-gate.md` when the symptom is visual, responsive,
interaction, focus, accessibility, TUI, or CLI presentation behavior.

Reproduce the symptom or establish the strongest available failure signal before
changing behavior. Use cognition to locate likely owners, boundaries, and
verification surfaces, then confirm all claims against logs, configuration,
tests, runtime output, and live source.

Maintain a small set of ranked hypotheses and choose evidence that separates
them. Distinguish the visible symptom from the failure mechanism. Once evidence
supports a root cause, apply the minimum coherent fix and add or update a
regression test when practical. When logs are insufficient, add bounded
instrumentation or request a precise user-log packet instead of guessing.

Re-run the original reproduction and relevant surrounding verification.
For a UI regression, reproduce and recapture the same real entry point,
viewport, and state after the fix; source inspection or component tests cannot
prove a visual symptom resolved.
Delegate only independent evidence lanes or an independent review that improves
confidence. Persist a debug session only when the investigation spans turns or
needs recovery; create it from the advanced session asset rather than the
classic multi-agent debug template.

After a verified fix, close out cognition with canonical workflow `debug`.
Finish as resolved, blocked, or unresolved, citing root-cause evidence, changes,
verification, and remaining uncertainty.
