Trigger: when explaining how `sp-specify` or `sp-quick` consumes a ready discussion contract.

Purpose: preserve downstream fidelity while preventing duplicate source sweeps and human-oriented handoff material.

Preserved Contract: consumers read canonical JSON, inherit confirmed truth by stable reference, and return integrity defects to `sp-discussion`.

## Downstream Consumption

Consumers select `.specify/discussions/<slug>/handoff-to-specify.json` through `specify-runtime artifact show`, verify ready/user-confirmed gates and current `review_digest`, then query only required contract fields and evidence refs.

Do not require a Markdown companion. `specification-input.md`, `discussion-state.md`, and other discussion source files are not fallback handoffs. Do not scan discussion logs or checkpoint documents unless a named evidence reference is stale, missing, or contradictory. Do not rebuild `discussion_decision_digest`, flatten the selected direction, or re-ask confirmed questions when `semantic_delta` is empty.

At the discussion routing gate, present both paths and their eligibility, explain any blocker, and give a complexity-informed recommendation among eligible paths: `sp-quick` for bounded, well-understood direct delivery with task-local planning; `sp-specify` for high-complexity or ambiguous work, interacting capabilities or systems, architecture/data migration/security/compliance/rollout concerns, broad acceptance obligations, or durable specification traceability. Task size alone is not a hard routing ceiling. The user's final choice controls the route, even when it differs from the recommendation. The confirmed contract records that selected consumer: `sp-specify` compiles it into `spec-contract.json`, while `sp-quick` consumes it for direct delivery. After successful consumption, bind downstream evidence to `source_contract` and `review_digest`, then mark the discussion consumed.
