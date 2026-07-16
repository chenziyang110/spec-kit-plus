# Clarification contract

Clarification repairs an existing specification; it is not a second discovery
transcript. Keep a compact ledger of question, why it matters, available
evidence, user answer or accepted assumption, and affected requirement IDs.

Prefer high-leverage questions that eliminate multiple downstream branches.
Do not ask about implementation preferences unless they are already a product
constraint. Do not use an open question to hide a resolvable repository fact.

After each answer, propagate the semantic change through the machine contract
and only the views it actually affects. Recheck acceptance, exclusions,
must-preserve behavior, and consequence obligations. A clarification is done
when planning has one coherent contract, not merely when every question has a
text response.

Keep the Classic clarification evidence surfaces even when delegation is not
needed: `clarification/handoffs/`, `clarification/evidence-index.json`, and
`clarification/checkpoints.ndjson`. Preserve prior records. Every accepted lane
must name the `spec.md`, `alignment.md`, `context.md`, or `references.md`
section that consumed it, or carry an explicit deferral/blocker disposition.
