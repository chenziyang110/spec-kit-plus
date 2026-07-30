{{spec-kit-include: ../common/user-input.md}}

## Objective

Turn a new or changed feature request into a reviewed, planning-ready specification package through a concise collaborative flow: understand context, clarify one high-impact question at a time, compare approaches, confirm the spec shape, write artifacts, self-review, and ask the user to review before planning.

## Context

- Primary inputs: the user's request for discovery mode, or canonical agent-only `handoff-to-specify.json` queried through `specify-runtime artifact show` for compile mode; current repository context, passive memory, and project cognition are loaded only when the contract lacks fresh evidence for a planning-relevant claim.
- Authoritative output: agent-only `spec-contract.json`. `spec.md` is the project-facing rendering; `alignment.md`, `context.md`, `references.md`, and requirements diagnostics are conditional views with independent value. `workflow-state.md` is resume state, not phase handoff truth.
- This command is specification-only. It is not permission to implement code.

## Process

- If initial `workflow-state.md` is absent, create its fixed shape with `artifact scaffold --kind workflow-state --path <feature-dir>/workflow-state.md`; resume it with targeted `artifact show` and fresh leased `artifact patch` calls. Never submit or reconstruct the whole state document.
- Before creating a feature workspace, classify arguments as either a normal feature description or a discussion handoff path/JSON path/slug. If no arguments are supplied, use exactly one unconsumed `status: handoff-ready` discussion whose `next_command` is `/sp.specify` or `sp-specify`; if there are zero or multiple candidates, stop and ask for a feature description or specific handoff.
- For a discussion handoff, require canonical JSON `status: handoff-ready`, `planning_gate_status: ready`, `quality_gate.status: user_confirmed`, matching `quality_gate.confirmed_digest` and `review_digest`, zero hard unknowns, zero open conflicts, and complete protected `MP-*`, `CA-###`, evidence, and settled-decision coverage.
- If a discussion workspace contains `specification-input.md` or looks specification-ready but lacks the ready JSON contract, stop with `blocked_by_handoff_integrity` and route back to `sp-discussion`; only `specify-runtime discussion write-handoff` may create or repair `handoff-to-specify.json`.
- Derive the feature description from `handoff_goal` plus the implementation target summary. Do not pass the raw handoff path, JSON path, or slug to the create-feature script as the feature description.
- Explore project context only enough to understand ownership, constraints, adjacent surfaces, and source evidence.
- If invoked from `sp-discussion`, read the canonical contract once, reuse its context capsule and decision digest, and inspect supporting discussion files only when a named evidence reference is stale, missing, or contradictory.
- If invoked from `sp-discussion`, keep the source discussion slug; after the artifact CLI scaffolds, patches, and validates `spec-contract.json`, run `specify-runtime discussion mark-consumed`.
- Extract every upstream capability-like signal from those sources and assign exactly one disposition: `preserved`, `in_scope`, `deferred`, `dropped`, or `clarification_blocker`.
- Ask one high-impact question at a time when the answer can change scope, acceptance, architecture, compatibility, security, data shape, external integration, or downstream planning.
- Decompose ambiguous terms such as capability, real, usable, works, end-to-end, fetch, probe, health, model, endpoint, integration, auth, `new` command, `<tool> new`, create, scaffold, authoring, template creation, authoring workflow, CLI path, TUI path, `能力`, `真实`, and `可用` before compiling the spec.
- Treat create/scaffold/`new` command/authoring workflow wording as an operation-shaped capability signal. If surface minimization changes the entry point, preserve the capability operation through an explicit TUI route, core API, public CLI command, or user-confirmed deferral; do not downgrade it to manual copy docs or static template-only support without confirmation.

## UI Reference Input

- First classify UI applicability independently of whether the user supplied a
  screenshot. New or changed user-visible screens, components, layouts,
  navigation, interaction flows, responsive behavior, visual states, TUI
  layouts, or CLI presentation are UI-bearing work.
- For substantive UI-bearing work, require `ui-brief.md` even when there is no
  external reference. Query approved `DESIGN.md` through `specify-runtime artifact show`; the leader may compile that brief from the returned contract,
  existing product surfaces, and confirmed experience requirements.
  A narrow copy-only or existing-pattern state fix may record why a separate
  brief adds no decision value and use a precise `spec.md#...` design-contract
  reference as `design_contract.ui_brief_ref`; the UI contract is never omitted.
- Treat `DESIGN.md` with `design_system.status: bootstrap` as not ready for a
  new direction. Route product-wide or high-visibility design decisions to
  `sp-design`; do not inherit its generic starter tokens as product intent.
- When approved design provenance names
  `.specify/design/previews/round-NN.html#<direction-id>`, query the preview and
  its approval/manifest/handoff sidecars only through targeted
  `specify-runtime artifact show` calls, then preserve that exact project-level
  visual reference, approval sidecar,
  preview/manifest/handoff SHA-256 values, immutable handoff reference,
  applicable `DS-*` decisions, and applicable `DH-*` implementation contracts,
  including component/state, density, responsive, motion-token,
  reduced-motion, and visual-acceptance rules. Select the required handoff rows
  by ID and preserve their structured values; do not paraphrase or reconstruct
  them from the preview. A later feature-level `ui-target.html` refines concrete
  composition and does not replace the approved preview or handoff.
- Detect screenshots, HTML/CSS mockups, Tailwind/shadcn/React/Vue/Svelte snippets, Figma exports, reference URLs, existing product pages, or matching-language such as "make it like this", "basically the same", "copy this layout", or "use this as the design".
- When UI reference input exists, ask for the fidelity mode unless the user already stated it:
  - `approximate` by default: preserve layout, density, hierarchy, visual rhythm, component structure, and primary interactions.
  - `high`: require visual comparison and deviation notes.
  - `inspiration`: extract principles only and avoid similar-looking output.
- Use `choose_ui_reference_lane_dispatch(command_name="specify", snapshot, workload_shape)` before dispatching UI reference work.
- Record `lane_mode: ui-reference-artifact`, `dispatch_shape`, `execution_surface`, `workflow_status`, `blocked_reason`, and whether inline fallback was user approved.
- The `sp-specify` leader must not directly parse UI references and write the UI contract when UI reference input is present. The leader dispatches and validates the lane.
- The UI reference lane creates `ui-reference-notes.md` with `artifact scaffold --kind ui-reference-notes` and `ui-brief.md` with `artifact scaffold --kind ui-brief`, then patches only semantic sections through fresh leases. It creates optional `ui-target.html` only through `specify-runtime design ui-target`; it never reads and reproduces any installed template.
- Do not treat this as a read-only evidence lane; source code, tests, app styling, component implementation, package managers, builds, and app servers remain forbidden.
- In discovery mode, present materially different approaches when they change behavior, boundary, compatibility, or acceptance proof. In compile mode, inherit the confirmed approach and emit only its semantic delta.
- Do not repeat user review for an unchanged confirmed discussion contract. Ask again only when specification compilation changes scope, behavior, risk acceptance, target boundary, or another user-owned decision.
- When entered through `sp-auto` with `auto_default_recommendation: true`, automatically accept a single safe recommended approach or section-shape option instead of stopping only for a `1`/`2`/`3` reply; do not use this to confirm scope reduction, dropped upstream signals, out-of-scope conflicts, or unresolved planning-critical ambiguity.
- Scaffold `spec-contract.json` first with `artifact scaffold --kind spec-contract`, refine it with targeted `artifact patch`, and patch named sections in the prerequisite-script-created `spec.md` skeleton through its registered owner; never write or resubmit those files directly.
- Ask the user only about a non-empty `semantic_delta` or unresolved user-owned decision before recommending exactly one next command: `/sp.plan`, `/sp.clarify`, or `/sp.deep-research`.

## Output Contract

- Let `artifact scaffold --kind spec-contract` expand `templates/spec-contract-template.json`, then mutate only targeted JSON pointers through leased `artifact patch`. Query `spec.md` with `artifact show` and patch only named sections; route conditional views through their registered artifact owners.
- Treat feature-bootstrap `brainstorming/*` state as derived compatibility artifacts: query a named record only through `specify-runtime artifact show` and never mutate it. When compile mode requires `brainstorming/handoff-to-specify.json`, submit only `semantic_delta`, `required_refs`, `blockers`, and `recovery` inline through `specify-runtime discussion bind-consumer <slug> --feature-dir <feature-dir> --input-json '<transition-json>'`; the runtime binds source/digest/status/next action and writes the pointer.
- When UI reference input exists, require `ui-reference-notes.md` created through `artifact scaffold --kind ui-reference-notes`; for every
  substantive concrete UI surface, require `ui-brief.md` whether or not a
reference was supplied; create `ui-target.html` only through `specify-runtime design ui-target` when a disposable visual
  target materially reduces ambiguity. Scaffold it with
  `{{specify-subcmd:specify-runtime design ui-target --out <FEATURE_DIR>/ui-target.html}}`,
  configure its embedded manifest and candidate status, then require
  `{{specify-subcmd:specify-runtime design ui-target-lint <FEATURE_DIR>/ui-target.html --level ready}}`.
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
