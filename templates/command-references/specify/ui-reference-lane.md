Trigger: when screenshots, UI references, design exports, mockups, or existing UI pages shape the requirement.

Purpose: preserve UI reference lane routing, fidelity mode handling, and Reference-Implementation evidence rules.

Preserved Contract: UI reference work must preserve lane dispatch, static target validation, fidelity evidence, and accepted deviation semantics.

## UI Reference Lane

**UI reference input handling**:
- Preserve an approved change-level
  `.specify/design/changes/<UD-ID>/previews/round-NN.<html|png|jpg|jpeg|webp>#<direction-id>` as
  `approved_visual_ref` together with its immutable handoff reference and
  registered design ref/hash and preview/manifest/handoff digests; do not collapse either artifact into prose
  or replace them with the feature-level `ui-target.html`. Carry applicable
  `DS-*` decision IDs and `DH-*` contract IDs into the UI brief, selecting and
  copying their structured rows instead of rewriting their meaning.
- Preserve `style_authority` exactly. Existing-product feature/partial-page work
  inherits the live UI and cannot select a style skill; only an explicitly
  authorized exact full-page overhaul may carry bounded style-delta surfaces,
  while `global-shell` and `shared-components` remain protected.
- Detect screenshots, HTML/CSS mockups, UI framework snippets, design exports, UI reference URLs or existing UI pages, and matching-language such as "make it like this" as UI reference input.
- Treat those inputs as dimension-limited evidence, never a complete product
  contract. When a reference, live/runnable product, recording, source code, or
  prior implementation governs the requested UI, build and validate
  `source_continuity`: inspectable authority refs; complete surface discovery;
  action bindings with `business_outcome`, side effects, final state, and
  source-target verification; asset bindings with provenance and target refs;
  and an empty `unresolved_gaps` gate. A screenshot or HTML file cannot prove
  hidden surfaces or business behavior by itself.
- Record icon/image/font/media semantics in `asset_bindings`. A raw character,
  emoji, or Unicode glyph cannot satisfy a required icon; use
  `forbid-character-substitution` unless the user explicitly approves an
  intentional text symbol as `approved-text-symbol`.
- For a chat-only binary attachment, pass the runtime image item directly when supported or import its runtime-provided local path with `specify-runtime evidence import --file <local-path> --scope ui-reference --source chat-attachment --provenance user-provided`; reference the returned `object_ref` and evidence record. Never copy or materialize a project file directly.
- Give every reference its own use intent: `exact`, `preserve-structure`,
  `inspiration`, `extract-tokens`, or `do-not-copy`. Intent controls permitted
  use; fidelity controls closeness and does not replace intent.
- Ask the user which fidelity mode applies when not already explicit: `approximate` (default), `high`, or `inspiration`.
- Use `choose_ui_reference_lane_dispatch(command_name="specify", snapshot, workload_shape)` and record `lane_mode: ui-reference-artifact`.
- For `approximate` and `high`, native subagents are required by default; if native subagents are unavailable, follow the decision from `choose_ui_reference_lane_dispatch` and proceed inline only when it returns a gated `leader-inline` fallback with explicit user approval recorded, otherwise block with the missing capability instead of guessing.
- For `inspiration`, inline fallback may proceed only after `choose_ui_reference_lane_dispatch` returns a gated `leader-inline` soft-risk decision with safe lane and contract-ready state satisfied.
- Dispatch the UI reference lane with registered artifact owners for notes/brief and `specify-runtime design ui-target` for optional `ui-target.html`.
- Carry the exact validated `source_continuity` object from reference notes into
  the UI brief, plan UI contract, every applicable task/worker packet, and
  Review. Specify owns unresolved product meaning; implementation details do
  not authorize inventing a business action.
- This lane is a Specify-owned intake path, not a reason to rerun Specify after
  an unchanged planning-ready spec. A late design overlay uses
  `formal-post-specify` and returns to Plan; only requirements changes reopen
  this lane.
- Validate that `ui-target.html`, when present, is a single-file,
  low-dependency review artifact with an embedded
  `spec-kit-ui-target-manifest-v1`. It may use bounded inline JavaScript only
  for viewport/state selection, keyboard-accessible review navigation,
  direction/reference deep links, capture mode, and purposeful motion replay.
  It must have no inline event-handler attributes such as `onclick`, external
  CSS/JS, CDN, network calls, persistence, analytics, business logic, or
  production-source claim. Preserve information density over decorative
  polish and bind the approved preview/direction/handoff digests plus applicable
  `DS-*` decision IDs and `DH-*` handoff contract IDs. Scaffold and validate it with
  `{{specify-subcmd:specify-runtime design ui-target --out <FEATURE_DIR>/ui-target.html}}`
  and
  `{{specify-subcmd:specify-runtime design ui-target-lint <FEATURE_DIR>/ui-target.html --level ready}}`.
- For `approximate` and `high`, activate the `Reference-Implementation` profile contract, require `Fidelity Requirements`, and persist canonical `required_evidence` terms: `reference source evidence`, `fidelity criteria`, `verification entry points`, `difference inventory`, and `accepted deviations`; for `high`, require a deviation log as an artifact form for `difference inventory` / `accepted deviations`.
- The task contract uses canonical platform-neutral evidence kinds
  `structure_snapshot`, `visual_capture`, and `runtime_diagnostics`; for web,
  capture accessibility/DOM structure, viewport screenshots, and console/runtime
  output from the real entry point.
