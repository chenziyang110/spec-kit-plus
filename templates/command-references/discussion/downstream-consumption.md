Trigger: when explaining how `sp-specify` or `sp-quick` consumes a ready discussion contract.

Purpose: preserve downstream fidelity while preventing duplicate source sweeps and human-oriented handoff material.

Preserved Contract: consumers read canonical JSON, inherit confirmed truth by stable reference, and return integrity defects to `sp-discussion`.

## Downstream Consumption

Consumers select `.specify/discussions/<slug>/handoff-to-specify.json` through `specify-runtime artifact show`, verify ready/user-confirmed gates and current `review_digest`, then query only required contract fields and evidence refs.

Do not require a Markdown companion. `specification-input.md`, `discussion-state.md`, and other discussion source files are not fallback handoffs. Do not scan discussion logs or checkpoint documents unless a named evidence reference is stale, missing, or contradictory. Do not rebuild `discussion_decision_digest`, flatten the selected direction, or re-ask confirmed questions when `semantic_delta` is empty.

`sp-specify` compiles the contract into `spec-contract.json` when the user selected a formal spec-first path. `sp-quick` consumes it for direct delivery without a task-size or consequence-breadth ceiling. The target boundary and next consumption path come from the confirmed contract and explicit workflow choice. After successful consumption, bind downstream evidence to `source_contract` and `review_digest`, then mark the discussion consumed.
