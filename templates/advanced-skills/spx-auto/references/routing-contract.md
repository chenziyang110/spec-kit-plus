# Auto routing contract

For every feature candidate, first run `workflow show`, then `workflow next`.
`FEATURE_DIR/workflow-runtime.json` is the primary required-stage phase lock.
Consume its structured `next_argv`: `workflow complete-stage` routes to the
current stage owner, while `workflow transition --to <stage>` routes to that
destination and is passed through exactly. Never reconstruct runtime flags from
prose or infer a successor from Markdown. Active `accept` returning
`workflow closeout` routes to the current accept owner; only completed `accept`
has no successor. `workflow-state.md` remains rich
workflow-owned resume/evidence context; it may add an auxiliary gate but cannot
skip or reverse the runtime stage. Legacy `next_command`/`active_command`
heuristics are fallback only for noncanonical auxiliary state when no runtime
file exists.

A blocked runtime intentionally has no `next_argv`. Preserve its tutorial and
wait for the declared evidence; when available, fill only the required evidence
input in `data.resolution_action` and execute its runtime-owned base argv.
`show_argv` refreshes state but does not resolve it.

When rich state contains evidence that an upstream required stage is invalid,
do not infer a reverse route from its prose alone. Use `workflow reopen` with
the current revision, compact reason, sanitized evidence, and complete
invalidated-artifact set when the record is sufficient. Resume an already active
mapped owner; reactivate the same completed owner through reopen. Otherwise
route to analyze or the current owner to establish a valid reopen decision. A
blocked runtime must first use `workflow resolve` with evidence, and acceptance
findings use `accept route-repair`.

Use the lane registry only to discover candidates, then reconcile it with real
state, artifacts, and any materialized worktree. A recorded upstream gate
outranks an implementation tracker or later artifact. Stop on an `uncertain`
lane, conflicting states, or anything other than exactly one unique safe
candidate; report the evidence and smallest repair instead of guessing.

Choose the first applicable trustworthy route:

- new/high-visibility UI direction, redesign, or UI work blocked by missing or
  bootstrap `DESIGN.md`: `spx-design`;
- active durable team batch: `spx-implement-teams`;
- trusted completed system Review whose fresh `human-acceptance.json` is not
  `accepted`: `spx-accept`;
- active Review, or trusted completed implementation whose Review is missing,
  stale, blocked, repairing, or not approved: `spx-review`;
- completed independent lane awaiting closeout: `spx-integrate`;
- active implementation lane or ready tracked feature work: `spx-implement`;
- active bounded quick workspace: `spx-quick`;
- active debug session or unknown failure mechanism/regression: `spx-debug`;
- active discussion not yet handoff-ready: `spx-discussion`;
- confirmed ready discussion handoff awaiting consumption: `spx-specify`;
- active PRD reconstruction scan or evidence gap: `spx-prd-scan`;
- reconstruction-ready PRD scan awaiting exports: `spx-prd-build`;
- cognition baseline explicitly requires rebuild: `spx-map-rebuild`;
- scan-ready cognition workbench awaiting publication: `spx-map-build`;
- active or required cognition scan without scan readiness: `spx-map-scan`;
- interrupted or externally changed existing map with no higher active owner:
  `spx-map-update`;
- existing feature has planning-blocking ambiguity or contradictory acceptance:
  `spx-clarify`;
- new feature intent or acceptance is missing or not planning-ready:
  `spx-specify`;
- planning-ready spec has unresolved implementation-chain feasibility:
  `spx-deep-research`;
- planning-ready spec lacks a coherent technical design: `spx-plan`;
- ready plan lacks an executable task graph: `spx-tasks`;
- persisted consistency gate is required or stale: `spx-analyze`;
- ready tasks remain and prerequisites agree: `spx-implement`;
- new request is truly trivial and passes the fast gate: `spx-fast`;
- new bounded non-trivial request needs lightweight state: `spx-quick`;
- workflow-artifact explanation: `spx-explain`;
- other read-only project question: `spx-ask`.

Do not route from a filename alone. Confirm the relevant state contract,
artifact readiness, live diff, and blocker. If a terminal marker conflicts with
missing verification or repository changes, resume the owning workflow rather
than declaring completion.
