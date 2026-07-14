# Execution lifecycle

Treat task checkboxes and prior status as claims until the live diff, required
evidence, and fresh verification support them. On an uncertain resume or a
terminal-looking tracker, run
`{{specify-subcmd:implement resume-audit --feature-dir <feature-dir> --format json}}`
before editing.

For each ready task:

- confirm authoritative inputs, dependencies, acceptance, likely write scope,
  and must-preserve obligations;
- establish RED or a credible before-state for behavior changes;
- implement the complete outcome and update generated/mirrored consumers;
- verify the real entry point and material boundaries, not only an isolated
  helper;
- record changed paths, checks, obligation evidence, blockers, and recovery.

For UI tasks, apply the packet `ui_contract` as binding scope. Run the visual convergence loop at the real entry point: render the required states and
viewports, capture stable screenshots or platform output, inspect against
`DESIGN.md`, `ui-brief.md`, prior surfaces, and original references, repair
concrete drift, then recapture. Check overflow, console, keyboard/focus, and
accessibility when applicable. Persist difference inventory and accepted
deviations for approximate/high fidelity. tests passed is not visual acceptance;
unavailable comparison is `pending-human-review` with an exact review target.
Before accepting the task, persist its lifecycle `ui_verification` with
`applicable: true`, passing contract check, concrete evidence refs, visual
comparison, fidelity status, reviewer, and human-review ref when relevant.
`pending-human-review` blocks accepted closeout until that review is resolved.

Review on drift, parallel joins, write-scope changes, validation failure,
worker concern, obligation conflict, real-entrypoint gaps, or an oversized
unreviewed window. Repair only understood local failures; reopen planning or
debugging when upstream truth or root cause is unknown.

Before completion, run
`{{specify-subcmd:implement closeout --feature-dir <feature-dir> --format json}}`
when available. Durable team execution and independent-lane integration have
their own explicit SPX skills; do not invent either protocol inside this path.
