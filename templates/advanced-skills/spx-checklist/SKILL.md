---
name: spx-checklist
description: Focused requirements-quality checklist workflow for advanced coding models. Use when a feature needs unit tests for the written requirements or planning package, not implementation testing.
---

# SPX Checklist

Read `references/project-cognition.md`, using cognition intent `plan`, and
`references/checklist-contract.md`. Resolve the active feature with the
installed prerequisite script. Use `assets/checklist.md` only as the compact
shape for a new checklist.

Choose the checklist domain and audience from the request and current artifacts.
Generate questions that test whether requirements are complete, unambiguous,
consistent, observable, traceable, and explicit about boundaries and failure
behavior. Use cognition and live source only to identify real vocabulary,
owners, consumers, and likely blind spots—not to test the implementation.

Write a feature-local checklist under the established checklist directory and
preserve existing checklist IDs when revising it. Each item must be an answerable
question about the quality of written requirements or planning decisions, with
a traceability hint where useful. Avoid generic items that would pass every
feature.

Treat an existing checklist as append-only: retain its items and allocate new
IDs after the current maximum. Deduplicate equivalent questions before writing
and preserve traceability to the requirement, section, or explicit gap.

Do not edit the specification, plan, tasks, production source, or tests in this
workflow. Report the created checklist and the upstream workflow that should
repair any discovered gap. Checklist completion does not by itself prove the
software works. This invocation authorizes only this workflow stage; do not
invoke another workflow in this run.
