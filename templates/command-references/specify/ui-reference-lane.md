Trigger: when screenshots, UI references, design exports, mockups, or existing UI pages shape the requirement.

Purpose: preserve UI reference lane routing, fidelity mode handling, and Reference-Implementation evidence rules.

Preserved Contract: UI reference work must preserve lane dispatch, static target validation, fidelity evidence, and accepted deviation semantics.

## UI Reference Lane

**UI reference input handling**:
- Preserve an approved project-level
  `.specify/design/previews/round-NN.html#<direction-id>` as
  `approved_visual_ref` together with its immutable handoff reference and
  preview/manifest/handoff digests; do not collapse either artifact into prose
  or replace them with the feature-level `ui-target.html`. Carry applicable
  `DS-*` decision IDs and `DH-*` contract IDs into the UI brief, selecting and
  copying their structured rows instead of rewriting their meaning.
- Detect screenshots, HTML/CSS mockups, UI framework snippets, design exports, UI reference URLs or existing UI pages, and matching-language such as "make it like this" as UI reference input.
- For a chat-only binary attachment, pass the runtime image item directly when supported or import its runtime-provided local path with `specify-runtime evidence import --file <local-path> --scope ui-reference --source chat-attachment --provenance user-provided`; reference the returned `object_ref` and evidence record. Never copy or materialize a project file directly.
- Give every reference its own use intent: `exact`, `preserve-structure`,
  `inspiration`, `extract-tokens`, or `do-not-copy`. Intent controls permitted
  use; fidelity controls closeness and does not replace intent.
- Ask the user which fidelity mode applies when not already explicit: `approximate` (default), `high`, or `inspiration`.
- Use `choose_ui_reference_lane_dispatch(command_name="specify", snapshot, workload_shape)` and record `lane_mode: ui-reference-artifact`.
- For `approximate` and `high`, native subagents are required by default; if native subagents are unavailable, follow the decision from `choose_ui_reference_lane_dispatch` and proceed inline only when it returns a gated `leader-inline` fallback with explicit user approval recorded, otherwise block with the missing capability instead of guessing.
- For `inspiration`, inline fallback may proceed only after `choose_ui_reference_lane_dispatch` returns a gated `leader-inline` soft-risk decision with safe lane and contract-ready state satisfied.
- Dispatch the UI reference lane with registered artifact owners for notes/brief and `specify-runtime design ui-target` for optional `ui-target.html`.
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
