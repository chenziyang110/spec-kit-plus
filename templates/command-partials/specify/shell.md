{{spec-kit-include: ../common/user-input.md}}

## Objective

Turn a new or changed feature request into a reviewed, planning-ready specification package through a concise collaborative flow: understand context, clarify one high-impact question at a time, compare approaches, confirm the spec shape, write artifacts, self-review, and ask the user to review before planning.

## Context

- Primary inputs: the user's request, current repository context, passive memory, project cognition only as advisory navigation, and discussion source files when a handoff-ready discussion is supplied or uniquely discoverable.
- Authoritative outputs: `spec.md`, `alignment.md`, `context.md`, `references.md` when useful, `workflow-state.md`, `checklists/requirements.md`, and a minimal `brainstorming/handoff-to-specify.json` compatibility handoff.
- This command is specification-only. It is not permission to implement code.

## Process

- Create or resume the feature workspace and `workflow-state.md`.
- Before creating a feature workspace, classify arguments as either a normal feature description or a discussion handoff path/JSON path/slug. If no arguments are supplied, use exactly one unconsumed `status: handoff-ready` discussion whose `next_command` is `/sp.specify` or `sp-specify`; if there are zero or multiple candidates, stop and ask for a feature description or specific handoff.
- For a discussion handoff, require the Markdown/JSON pair, `handoff_status: handoff-ready` or `discussion-state.md` `status: handoff-ready`, `planning_gate_status: ready`, `quality_gate.status: user_confirmed`, zero hard unknowns, zero open conflicts, a `Handoff Reviewer Guide`, and no Markdown/JSON drift in protected `MP-*`, `CA-###`, source evidence, or settled-decision coverage.
- If a discussion workspace contains `specification-input.md` or looks specification-ready but lacks the ready Markdown/JSON handoff pair, stop with `blocked_by_handoff_integrity` and route back to `sp-discussion` to write or repair `handoff-to-specify.md` and `handoff-to-specify.json`; do not ask the user to confirm `specification-input.md` as the feature input.
- Derive the feature description from `handoff_goal` plus the implementation target summary. Do not pass the raw handoff path, JSON path, or slug to the create-feature script as the feature description.
- Explore project context only enough to understand ownership, constraints, adjacent surfaces, and source evidence.
- If invoked from `sp-discussion`, re-read the selected `handoff-to-specify.md` and `.json`, then read the handoff-declared source files. At minimum inspect `discussion-log.md`, `requirements.md`, and `open-questions.md` when they exist; inspect `technical-options.md` and `project-context.md` when present or named.
- If invoked from `sp-discussion`, keep the source discussion slug from `.specify/discussions/<slug>/handoff-to-specify.md`; after the feature package is written and self-reviewed, run `specify discussion mark-consumed <slug> --feature-dir "$FEATURE_DIR"` or manually write `handoff_consumption_status: consumed`, `consumed_by_feature_dir: $FEATURE_DIR`, `status: completed`, and `next_command: none`.
- Extract every upstream capability-like signal from those sources and assign exactly one disposition: `preserved`, `in_scope`, `deferred`, `dropped`, or `clarification_blocker`.
- Ask one high-impact question at a time when the answer can change scope, acceptance, architecture, compatibility, security, data shape, external integration, or downstream planning.
- Decompose ambiguous terms such as capability, real, usable, works, end-to-end, fetch, probe, health, model, endpoint, integration, auth, `new` command, `<tool> new`, create, scaffold, authoring, template creation, authoring workflow, CLI path, TUI path, `能力`, `真实`, and `可用` before compiling the spec.
- Treat create/scaffold/`new` command/authoring workflow wording as an operation-shaped capability signal. If surface minimization changes the entry point, preserve the capability operation through an explicit TUI route, core API, public CLI command, or user-confirmed deferral; do not downgrade it to manual copy docs or static template-only support without confirmation.

## UI Reference Input

- Detect screenshots, HTML/CSS mockups, Tailwind/shadcn/React/Vue/Svelte snippets, Figma exports, reference URLs, existing product pages, or matching-language such as "make it like this", "basically the same", "copy this layout", or "use this as the design".
- When UI reference input exists, ask for the fidelity mode unless the user already stated it:
  - `approximate` by default: preserve layout, density, hierarchy, visual rhythm, component structure, and primary interactions.
  - `high`: require visual comparison and deviation notes.
  - `inspiration`: extract principles only and avoid similar-looking output.
- Use `choose_ui_reference_lane_dispatch(command_name="specify", snapshot, workload_shape)` before dispatching UI reference work.
- Record `lane_mode: ui-reference-artifact`, `dispatch_shape`, `execution_surface`, `workflow_status`, `blocked_reason`, and whether inline fallback was user approved.
- The `sp-specify` leader must not directly parse UI references and write the UI contract when UI reference input is present. The leader dispatches and validates the lane.
- The writable UI reference lane may write only `ui-reference-notes.md`, `ui-brief.md`, and optional `ui-target.html` inside the active `FEATURE_DIR`.
- Do not treat this as a read-only evidence lane; source code, tests, app styling, component implementation, package managers, builds, and app servers remain forbidden.
- Present two or three approaches with trade-offs and a recommendation before committing to the spec shape.
- Present the spec sections for user approval before final artifact release.
- When entered through `sp-auto` with `auto_default_recommendation: true`, automatically accept a single safe recommended approach or section-shape option instead of stopping only for a `1`/`2`/`3` reply; do not use this to confirm scope reduction, dropped upstream signals, out-of-scope conflicts, or unresolved planning-critical ambiguity.
- Write the artifact package, then self-review for placeholders, contradictions, ambiguous requirements, silent scope narrowing, dropped upstream signals, out-of-scope conflicts, missing acceptance proof, and unconfirmed product minimization.
- Ask the user to review the written artifacts before recommending exactly one next command: `/sp.plan`, `/sp.clarify`, or `/sp.deep-research`.

## Output Contract

- Write or update `spec.md`, `alignment.md`, `context.md`, `workflow-state.md`, `checklists/requirements.md`, and `references.md` when useful.
- Write or update a minimal `brainstorming/handoff-to-specify.json` compatibility handoff with `version`, `status`, `entry_source`, `source_handoff`, `source_handoff_json`, `source_files_read`, `source_signal_disposition`, `must_preserve`, `coverage_status`, `planning_gate_status`, `hard_unknown_count`, `open_conflict_count`, and `quality_gate`.
- When UI reference input exists, require `ui-reference-notes.md`; when the feature has a concrete UI surface, require `ui-brief.md`; create `ui-target.html` only when a disposable visual target materially reduces ambiguity.
- For `approximate` and `high` UI reference fidelity, activate `Reference-Implementation`, populate `Fidelity Requirements`, persist canonical Reference-Implementation `required_evidence`, and record UI-specific labels only as aliases/mapping notes.
- `alignment.md` must record `Semantic Term Decisions`, `Upstream Intent Disposition`, and `Out-Of-Scope Conflicts` when relevant.
- Do not recommend `/sp.plan` while a capability-like upstream signal lacks disposition, an ambiguous high-impact term lacks confirmation, or an out-of-scope conflict lacks user confirmation.
- Report what was confirmed, what remains open, what was deferred or dropped, and the single valid next command.

## Guardrails

- Do not edit source code, tests, or implementation files from `sp-specify`.
- Do not treat the discussion handoff summary as complete when discussion source files exist.
- Do not silently narrow user scope, redefine broad capability terms, or convert the request into a smaller delivery without user confirmation.
- Do not require legacy brainstorming journals, stage manifests, lock JSON files, or replay artifacts for normal `sp-specify` completion.
- Do not treat this summary block as the workflow itself; the detailed contract below remains authoritative.
