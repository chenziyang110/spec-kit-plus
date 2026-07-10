Trigger: when explaining how `sp-specify` or `sp-quick` consumes a ready discussion contract.

Purpose: preserve downstream fidelity while preventing duplicate source sweeps and human-oriented handoff material.

Preserved Contract: consumers read canonical JSON, inherit confirmed truth by stable reference, and return integrity defects to `sp-discussion`.

## Downstream Consumption

Consumers select `.specify/discussions/<slug>/handoff-to-specify.json`, verify ready/user-confirmed gates and current `review_digest`, then read the agent requirement contract, required evidence refs, task-relevant obligations, and reopen conditions.

Do not require a Markdown companion. `specification-input.md`, `discussion-state.md`, and other discussion source files are not fallback handoffs. Do not scan discussion logs or checkpoint documents unless a named evidence reference is stale, missing, or contradictory. Do not rebuild `discussion_decision_digest`, flatten the selected direction, or re-ask confirmed questions when `semantic_delta` is empty.

`sp-specify` compiles the contract into `spec-contract.json`. `sp-quick` consumes it only when quick eligibility remains bounded. The target boundary and next consumption path come from the contract. After successful consumption, bind downstream evidence to `source_contract` and `review_digest`, then mark the discussion consumed.
