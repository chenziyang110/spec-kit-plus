# Issue export contract

External issue creation is a separately authorized side effect. Invocation
proves intent only when the target repository and task set are clear; ask for a
decision if either is ambiguous.

Bind the side effect to the canonical GitHub owner/repository parsed from
`remote.origin.url`. Display-name similarity, organization defaults, a selected
UI repository, or working credentials do not establish identity. No exact
match means no issue read/write batch may start.

Use stable task IDs as the idempotency key. Search existing issue titles,
bodies, labels, and any recorded mapping before creation. Preserve parent or
dependency relationships when supported; otherwise state dependencies plainly
without fabricating tracker links.

Return a compact mapping of task ID to existing/created issue ID and URL, plus
failures safe to retry. Never claim atomic success when the connector completed
only part of a batch.
