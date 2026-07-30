---
name: spx-checklist
description: Focused requirements-quality checklist workflow for advanced coding models. Use when a feature needs unit tests for the written requirements or planning package, not implementation testing.
---

# SPX Checklist

Read `references/project-learning.md` and apply its consume-capture policy.
Read `references/project-cognition.md`, using cognition intent `plan`, and
`references/checklist-contract.md`. Resolve the active feature with the
installed prerequisite script.

Choose the checklist domain and audience from the request and current artifacts.
Generate questions that test whether requirements are complete, unambiguous,
consistent, observable, traceable, and explicit about boundaries and failure
behavior. Use cognition and live source only to identify real vocabulary,
owners, consumers, and likely blind spots—not to test the implementation.

Build one compact semantic object with `title`, `purpose`, `feature`, and
ordered `categories[]`; each category has a heading and plain item strings with
no Markdown checkbox or `CHK###` prefix. Submit it only through
`specify-runtime artifact checklist --path <feature-dir>/checklists/<domain>.md
--input-json '<checklist-object>' --format json`. The CLI expands the installed
template, creates or appends atomically, and assigns globally unique IDs. Never
write, append, renumber, or submit checklist Markdown yourself. Each item must
be an answerable question about the quality of written requirements or planning
decisions, with a traceability hint where useful. Avoid generic items that
would pass every feature.

Treat an existing checklist as append-only: query it through `artifact show`
only when semantic deduplication requires its existing items, then let the
checklist CLI preserve old content and allocate new IDs. Preserve traceability
to the requirement, section, or explicit gap.

Do not edit the specification, plan, tasks, production source, or tests in this
workflow. Report the created checklist and the upstream workflow that should
repair any discovered gap. Checklist completion does not by itself prove the
software works. This invocation authorizes only this workflow stage; do not
invoke another workflow in this run.
