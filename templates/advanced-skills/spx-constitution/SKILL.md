---
name: spx-constitution
description: Project-governance workflow for advanced coding models. Use when project principles or development rules must be created, revised, or realigned before downstream specification or planning.
---

# SPX Constitution

Read `references/project-cognition.md`, using cognition intent `plan`, and
`references/constitution-contract.md`. Read `references/consequence-gate.md`
when a proposed principle changes security, compatibility, lifecycle, public
contracts, or recovery obligations.

Inspect `.specify/memory/constitution.md`, `.specify/memory/project-rules.md`,
`.specify/memory/learnings/INDEX.md`, relevant linked learning details, the
project handbook, and cognition-selected live evidence needed to understand
current practice. Read active feature `spec.md`, `plan.md`, `tasks.md`, and
`workflow-state.md` without editing them so the highest affected downstream
stage and exact re-entry route can be determined. Resolve conflicts between the
requested rule and established project constraints before editing.

Create or revise `.specify/memory/constitution.md` using the installed
constitution template and profiles when useful. Express each principle as a
clear obligation with rationale, scope, precedence, and an observable governance
effect. Preserve unrelated adopted principles and record amendment intent.
Classify the version change as MAJOR for incompatible governance removal or
redefinition, MINOR for a new or materially expanded principle/section, and
PATCH for clarification without semantic change. Use ISO `YYYY-MM-DD` dates for
ratification and last amendment.

Prepend a compact Sync Impact Report to the constitution. Record old/new
version; added, modified, and removed principles/sections; affected templates,
active artifacts, memory, and cognition surfaces; every pending follow-up; the
highest affected downstream stage with exact re-entry command; and unresolved
TODOs. The report must survive recovery and must not claim downstream updates
that this workflow did not perform.

This workflow owns the constitution only. Do not silently rewrite active specs,
plans, tasks, generated agent instructions, production code, or tests. Instead,
report which downstream artifacts or generated consumers may now be stale and
route the highest affected stage to `$spx-specify`, `$spx-plan`, `$spx-tasks`,
or `$spx-analyze`. Validate the edited constitution for unresolved placeholders,
contradictions, non-actionable language, version/date consistency, and a
complete Sync Impact Report. This invocation authorizes only this workflow
stage; report the highest affected downstream stage as a handoff and stop. Do
not invoke another workflow in this run.
