{{spec-kit-include: ../common/user-input.md}}

## Objective

Turn a new or changed feature request into a reviewed, planning-ready specification package through a concise collaborative flow: understand context, clarify one high-impact question at a time, compare approaches, confirm the spec shape, write artifacts, self-review, and ask the user to review before planning.

## Context

- Primary inputs: the user's request, current repository context, passive memory, project cognition only as advisory navigation, and discussion source files when a discussion handoff is supplied.
- Authoritative outputs: `spec.md`, `alignment.md`, `context.md`, `references.md` when useful, `workflow-state.md`, `checklists/requirements.md`, and a minimal `brainstorming/handoff-to-specify.json` compatibility handoff.
- This command is specification-only. It is not permission to implement code.

## Process

- Create or resume the feature workspace and `workflow-state.md`.
- Explore project context only enough to understand ownership, constraints, adjacent surfaces, and source evidence.
- If invoked from `sp-discussion`, read `handoff-to-specify.md` and `.json` when present, then read the handoff-declared source files. At minimum inspect `discussion-log.md`, `requirements.md`, and `open-questions.md` when they exist; inspect `technical-options.md` and `project-context.md` when present or named.
- Extract every upstream capability-like signal from those sources and assign exactly one disposition: `preserved`, `in_scope`, `deferred`, `dropped`, or `clarification_blocker`.
- Ask one high-impact question at a time when the answer can change scope, acceptance, architecture, compatibility, security, data shape, external integration, or downstream planning.
- Decompose ambiguous terms such as capability, real, usable, works, end-to-end, fetch, probe, health, model, endpoint, integration, auth, `能力`, `真实`, and `可用` before compiling the spec.
- Present two or three approaches with trade-offs and a recommendation before committing to the spec shape.
- Present the spec sections for user approval before final artifact release.
- Write the artifact package, then self-review for placeholders, contradictions, ambiguous requirements, silent scope narrowing, dropped upstream signals, out-of-scope conflicts, missing acceptance proof, and unconfirmed product minimization.
- Ask the user to review the written artifacts before recommending exactly one next command: `/sp.plan`, `/sp.clarify`, or `/sp.deep-research`.

## Output Contract

- Write or update `spec.md`, `alignment.md`, `context.md`, `workflow-state.md`, `checklists/requirements.md`, and `references.md` when useful.
- Write or update a minimal `brainstorming/handoff-to-specify.json` compatibility handoff with `version`, `status`, `entry_source`, `source_handoff`, `source_handoff_json`, `source_files_read`, `source_signal_disposition`, `must_preserve`, `coverage_status`, `planning_gate_status`, `hard_unknown_count`, `open_conflict_count`, and `quality_gate`.
- `alignment.md` must record `Semantic Term Decisions`, `Upstream Intent Disposition`, and `Out-Of-Scope Conflicts` when relevant.
- Do not recommend `/sp.plan` while a capability-like upstream signal lacks disposition, an ambiguous high-impact term lacks confirmation, or an out-of-scope conflict lacks user confirmation.
- Report what was confirmed, what remains open, what was deferred or dropped, and the single valid next command.

## Guardrails

- Do not edit source code, tests, or implementation files from `sp-specify`.
- Do not treat the discussion handoff summary as complete when discussion source files exist.
- Do not silently narrow user scope, redefine broad capability terms, or convert the request into a smaller delivery without user confirmation.
- Do not require legacy brainstorming journals, stage manifests, lock JSON files, or replay artifacts for normal `sp-specify` completion.
- Do not treat this summary block as the workflow itself; the detailed contract below remains authoritative.
