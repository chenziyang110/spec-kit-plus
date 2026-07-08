Trigger: when screenshots, UI references, design exports, mockups, or existing UI pages shape the requirement.

Purpose: preserve UI reference lane routing, fidelity mode handling, and Reference-Implementation evidence rules.

Preserved Contract: UI reference work must preserve lane dispatch, static target validation, fidelity evidence, and accepted deviation semantics.

## UI Reference Lane

**UI reference input handling**:
- Detect screenshots, HTML/CSS mockups, UI framework snippets, design exports, UI reference URLs or existing UI pages, and matching-language such as "make it like this" as UI reference input.
- Ask the user which fidelity mode applies when not already explicit: `approximate` (default), `high`, or `inspiration`.
- Use `choose_ui_reference_lane_dispatch(command_name="specify", snapshot, workload_shape)` and record `lane_mode: ui-reference-artifact`.
- For `approximate` and `high`, native subagents are required by default; if native subagents are unavailable, follow the decision from `choose_ui_reference_lane_dispatch` and proceed inline only when it returns a gated `leader-inline` fallback with explicit user approval recorded, otherwise block with the missing capability instead of guessing.
- For `inspiration`, inline fallback may proceed only after `choose_ui_reference_lane_dispatch` returns a gated `leader-inline` soft-risk decision with safe lane and contract-ready state satisfied.
- Dispatch the UI reference lane to write only `ui-reference-notes.md`, `ui-brief.md`, and optional `ui-target.html`.
- Validate that `ui-target.html`, when present, is static HTML/CSS only: single-file, low-dependency, no `<script>`, no inline event handlers such as `onclick`, no JS-driven behavior, no external CSS/JS, no CDN, no remote runtime dependencies, no production-source claim, and preserves information density over decorative polish.
- For `approximate` and `high`, activate the `Reference-Implementation` profile contract, require `Fidelity Requirements`, and persist canonical `required_evidence` terms: `reference source evidence`, `fidelity criteria`, `verification entry points`, `difference inventory`, and `accepted deviations`; for `high`, require a deviation log as an artifact form for `difference inventory` / `accepted deviations`.
- Keep UI-specific labels only as aliases/mapping notes, not persisted `required_evidence` values: `reference_source_evidence` alias -> `reference source evidence`; `ui_fidelity_criteria` alias -> `fidelity criteria`; `real_entrypoint_ui_evidence` alias -> `verification entry points` / existing `real_entrypoint_evidence` when real entrypoint proof is needed; `visual_comparison_or_human_review` alias -> `verification entry points` plus `accepted deviations` when human review is pending; `deviation_log` alias/artifact -> `difference inventory` / `accepted deviations`.
